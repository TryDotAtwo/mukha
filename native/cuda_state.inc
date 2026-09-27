// Included after the CUDA kernels; all device storage survives advance calls.
struct ff_cuda_model {
    static constexpr uint64_t mixed_checkpoint_version=3;
    uint32_t n, capacity;
    uint64_t edges, tick=0, identity;
    NeuralParams p;
    size_t ring_size;
    Real a,b,c;
    bool poisoned=false,mixed=false;
    Real graded_span=1,graded_step_factor=0;
    Buffer<uint64_t> row,col,next;
    Buffer<uint8_t> sense,graded,allowed,ts;
    Buffer<Real> w,v,g,ring,incoming,drive,tv,tg;
    Sparse sp;
    std::unique_ptr<Buffer<uint8_t>> scratch;

    ff_cuda_model(uint32_t count,uint64_t e,const uint64_t* rows,const uint32_t* columns,
                  const Real* weights,const uint8_t* sensory,NeuralParams params,uint32_t cap,
                  const uint8_t* graded_mask=nullptr,Real span=1):
        n(count),capacity(cap),edges(e),p(params),ring_size((size_t(params.delay_ticks)+1)*count),
        mixed(graded_mask!=nullptr),graded_span(span),
        row(size_t(count)+1),col(e),next(count),sense(count),graded(count),allowed(count),ts(size_t(count)*cap),
        w(e),v(count),g(count),ring(ring_size),incoming(count),drive(size_t(count)*cap),
        tv(size_t(count)*cap),tg(size_t(count)*cap) {
        std::vector<uint64_t> wide_col(edges);
        for(uint64_t j=0;j<edges;++j) wide_col[j]=columns[j];
        row.upload(rows,size_t(n)+1);col.upload(wide_col.data(),edges);w.upload(weights,edges);
        sense.upload(sensory,n);
        if(graded_mask) graded.upload(graded_mask,n);
        else check(cudaMemset(graded.p,0,n));
        identity=hash_bytes(&p,sizeof(p));
        identity=hash_bytes(rows,(size_t(n)+1)*sizeof(uint64_t),identity);
        identity=hash_bytes(columns,size_t(edges)*sizeof(uint32_t),identity);
        identity=hash_bytes(weights,size_t(edges)*sizeof(Real),identity);
        identity=hash_bytes(sensory,n,identity);
        if(mixed) {
            identity=hash_bytes(graded_mask,n,identity);
            identity=hash_bytes(&graded_span,sizeof(graded_span),identity);
            // A mixed checkpoint's delay ring contains dt-scaled release, not
            // raw clip(V) values. Bind that numerical meaning to its identity.
            constexpr char semantics[]="graded-release-dt-scaled-steady-weight-v3";
            identity=hash_bytes(semantics,sizeof(semantics)-1,identity);
        }
        check(cusparseCreate(&sp.handle));
        check(cusparseCreateCsr(&sp.matrix,n,n,edges,row.p,col.p,w.p,
              CUSPARSE_INDEX_64I,CUSPARSE_INDEX_64I,CUSPARSE_INDEX_BASE_ZERO,REAL_CUDA_TYPE));
        check(cusparseCreateDnVec(&sp.x,n,ring.p,REAL_CUDA_TYPE));
        check(cusparseCreateDnVec(&sp.y,n,incoming.p,REAL_CUDA_TYPE));
        const Real alpha=1,beta=0;
        size_t workspace=0;
        check(cusparseSpMV_bufferSize(sp.handle,CUSPARSE_OPERATION_NON_TRANSPOSE,&alpha,sp.matrix,
              sp.x,&beta,sp.y,REAL_CUDA_TYPE,CUSPARSE_SPMV_CSR_ALG2,&workspace));
        scratch=std::make_unique<Buffer<uint8_t>>(workspace);
        double aa=std::exp(-double(p.dt_ms)/p.membrane_ms),bb=std::exp(-double(p.dt_ms)/p.synapse_ms);
        a=Real(aa);b=Real(bb);
        graded_step_factor=Real(-std::expm1(-double(p.dt_ms)/p.synapse_ms));
        const auto coupling=lif_coupling(p.dt_ms,p.membrane_ms,p.synapse_ms);
        c=Real(coupling.value);
        if(coupling.changed_numerics) {
            constexpr char semantics[]="lif-near-equal-tau-expm1-v1";
            identity=hash_bytes(semantics,sizeof(semantics)-1,identity);
        }
        reset();
    }
    void reset() {
        poisoned=true;
        check(cudaMemset(ring.p,0,ring_size*sizeof(Real)));
        check(cudaMemset(incoming.p,0,size_t(n)*sizeof(Real)));
        initialize<<<(n+255)/256,256>>>(n,p.rest_mv,v.p,g.p,next.p);
        check(cudaGetLastError());check(cudaDeviceSynchronize());
        tick=0;poisoned=false;
    }
    void advance(uint32_t steps,const Real* input,Real* out_v,Real* out_g,uint8_t* out_s) {
        require(!poisoned,"model poisoned after device failure; reset or restore required");
        require(steps && steps<=capacity && input && out_v && out_g && out_s,"invalid chunk or arrays");
        require(tick<UINT64_MAX-uint64_t(steps)-p.refractory_ticks-p.delay_ticks-1,"tick overflow");
        size_t total=size_t(n)*steps;
        for(size_t i=0;i<total;++i) require(std::isfinite(input[i]),"nonfinite input");
        poisoned=true;
        drive.upload(input,total);
        const Real alpha=1,beta=0;
        for(uint32_t step=0;step<steps;++step,++tick) {
            Real* fired=ring.p+(tick%(size_t(p.delay_ticks)+1))*n;
            Real* delayed=ring.p+((tick+size_t(p.delay_ticks)+1-p.delay_ticks)%(size_t(p.delay_ticks)+1))*n;
            integrate<<<(n+255)/256,256>>>(n,tick,p,a,b,c,v.p,g.p,next.p,graded.p,graded_span,graded_step_factor,fired,allowed.p);
            check(cudaGetLastError());
            check(cusparseDnVecSetValues(sp.x,delayed));
            check(cusparseSpMV(sp.handle,CUSPARSE_OPERATION_NON_TRANSPOSE,&alpha,sp.matrix,sp.x,
                  &beta,sp.y,REAL_CUDA_TYPE,CUSPARSE_SPMV_CSR_ALG2,scratch->p));
            size_t offset=size_t(step)*n;
            finish<<<(n+255)/256,256>>>(n,tick,p,drive.p+offset,incoming.p,fired,allowed.p,sense.p,graded.p,v.p,g.p,next.p,
                                       tv.p+offset,tg.p+offset,ts.p+offset);
            check(cudaGetLastError());
        }
        check(cudaDeviceSynchronize());
        check(cudaMemcpy(out_v,tv.p,total*sizeof(Real),cudaMemcpyDeviceToHost));
        check(cudaMemcpy(out_g,tg.p,total*sizeof(Real),cudaMemcpyDeviceToHost));
        check(cudaMemcpy(out_s,ts.p,total,cudaMemcpyDeviceToHost));
        poisoned=false;
    }
    size_t checkpoint_size() const { return 64+size_t(n)*(2*sizeof(Real)+sizeof(uint64_t))+ring_size*sizeof(Real); }
    void save(uint8_t* output,size_t bytes) {
        require(!poisoned && output && bytes==checkpoint_size(),"invalid checkpoint output or poisoned model");
        size_t pos=64;
        auto copy=[&](const void* src,size_t size) { check(cudaMemcpy(output+pos,src,size,cudaMemcpyDeviceToHost));pos+=size; };
        copy(v.p,size_t(n)*sizeof(Real));copy(g.p,size_t(n)*sizeof(Real));copy(next.p,size_t(n)*sizeof(uint64_t));copy(ring.p,ring_size*sizeof(Real));
        uint64_t header[8]={CHECKPOINT_MAGIC,mixed?mixed_checkpoint_version:1ULL,n,edges,tick,identity,bytes-64,hash_bytes(output+64,bytes-64)};
        std::memcpy(output,header,64);
    }
    void load(const uint8_t* input,size_t bytes) {
        require(input && bytes==checkpoint_size(),"invalid checkpoint length");
        uint64_t header[8];std::memcpy(header,input,64);
        require(header[0]==CHECKPOINT_MAGIC && header[1]==(mixed?mixed_checkpoint_version:1ULL) && header[2]==n && header[3]==edges &&
                header[5]==identity && header[6]==bytes-64 && header[7]==hash_bytes(input+64,bytes-64),
                "checkpoint model identity, version or checksum mismatch");
        require(header[4]<UINT64_MAX-uint64_t(capacity)-p.refractory_ticks-p.delay_ticks-1,"checkpoint tick overflow");
        for(size_t offset=64;offset<64+size_t(n)*2*sizeof(Real);offset+=sizeof(Real)) {
            Real value;std::memcpy(&value,input+offset,sizeof(Real));require(std::isfinite(value),"nonfinite checkpoint state");
        }
        size_t ring_begin=64+size_t(n)*(2*sizeof(Real)+sizeof(uint64_t));
        for(size_t offset=ring_begin;offset<bytes;offset+=sizeof(Real)) {
            Real value;std::memcpy(&value,input+offset,sizeof(Real));
            require(mixed ? (std::isfinite(value) && value>=0 && value<=1) : (value==0.f || value==1.f),"invalid output ring");
        }
        poisoned=true;
        size_t pos=64;
        auto copy=[&](void* dst,size_t size) { check(cudaMemcpy(dst,input+pos,size,cudaMemcpyHostToDevice));pos+=size; };
        copy(v.p,size_t(n)*sizeof(Real));copy(g.p,size_t(n)*sizeof(Real));copy(next.p,size_t(n)*sizeof(uint64_t));copy(ring.p,ring_size*sizeof(Real));
        check(cudaMemset(incoming.p,0,size_t(n)*sizeof(Real)));check(cudaDeviceSynchronize());
        tick=header[4];poisoned=false;
    }
};

EXPORT const char* ff_cuda_probe_error() { return error.c_str(); }
EXPORT ff_cuda_model* ff_cuda_create(uint32_t n,uint64_t edges,const uint64_t* rows,const uint32_t* columns,
                                     const Real* weights,const uint8_t* sensory,NeuralParams p,uint32_t capacity) {
    try {
        error.clear();
        require(n && n<=INT32_MAX && capacity && rows && sensory && (edges==0 || (columns&&weights)),"invalid graph arrays");
        require(edges<=INT64_MAX && edges<=SIZE_MAX/8 && size_t(capacity)<=SIZE_MAX/n/sizeof(Real) &&
                size_t(p.delay_ticks)+1<=SIZE_MAX/n/sizeof(Real),"shape overflow");
        require(rows[0]==0 && rows[n]==edges,"invalid CSR endpoints");
        for(uint32_t i=0;i<n;++i) require(rows[i]<=rows[i+1] && sensory[i]<=1,"invalid row or sensory mask");
        for(uint64_t j=0;j<edges;++j) require(columns[j]<n && std::isfinite(weights[j]),"invalid edge");
        require(std::isfinite(p.dt_ms)&&p.dt_ms>0&&std::isfinite(p.membrane_ms)&&p.membrane_ms>0&&
                std::isfinite(p.synapse_ms)&&p.synapse_ms>0&&std::isfinite(p.rest_mv)&&
                std::isfinite(p.reset_mv)&&std::isfinite(p.threshold_mv),"invalid parameters");
        return new ff_cuda_model(n,edges,rows,columns,weights,sensory,p,capacity);
    } catch(const std::exception& ex) { error=ex.what();return nullptr; }
}
// Diagnostic mixed-output variant. The caller must source the mask and voltage span;
// no MaleCNS cell is assigned a graded phenotype by this API.
EXPORT ff_cuda_model* ff_cuda_create_mixed(uint32_t n,uint64_t edges,const uint64_t* rows,const uint32_t* columns,
                                           const Real* weights,const uint8_t* sensory,const uint8_t* graded_mask,
                                           Real graded_span,NeuralParams p,uint32_t capacity) {
    try {
        error.clear();
        require(graded_mask && std::isfinite(graded_span) && graded_span>0,"invalid graded configuration");
        require(n && n<=INT32_MAX && capacity && rows && sensory && (edges==0 || (columns&&weights)),"invalid graph arrays");
        for(uint32_t i=0;i<n;++i) require(graded_mask[i]<=1,"invalid graded mask");
        require(edges<=INT64_MAX && edges<=SIZE_MAX/8 && size_t(capacity)<=SIZE_MAX/n/sizeof(Real) &&
                size_t(p.delay_ticks)+1<=SIZE_MAX/n/sizeof(Real),"shape overflow");
        require(rows[0]==0 && rows[n]==edges,"invalid CSR endpoints");
        for(uint32_t i=0;i<n;++i) require(rows[i]<=rows[i+1] && sensory[i]<=1,"invalid row or sensory mask");
        for(uint64_t j=0;j<edges;++j) require(columns[j]<n && std::isfinite(weights[j]),"invalid edge");
        require(std::isfinite(p.dt_ms)&&p.dt_ms>0&&std::isfinite(p.membrane_ms)&&p.membrane_ms>0&&
                std::isfinite(p.synapse_ms)&&p.synapse_ms>0&&std::isfinite(p.rest_mv)&&
                std::isfinite(p.reset_mv)&&std::isfinite(p.threshold_mv),"invalid parameters");
        return new ff_cuda_model(n,edges,rows,columns,weights,sensory,p,capacity,graded_mask,graded_span);
    } catch(const std::exception& ex) { error=ex.what();return nullptr; }
}
EXPORT void ff_cuda_destroy(ff_cuda_model* m) { delete m; }
EXPORT int ff_cuda_advance(ff_cuda_model* m,uint32_t steps,const Real* input,Real* v,Real* g,uint8_t* spikes) {
    try { require(m,"null model");m->advance(steps,input,v,g,spikes);return 0; }
    catch(const std::exception& ex) { error=ex.what();return -1; }
}
EXPORT int ff_cuda_reset(ff_cuda_model* m) {
    try { require(m,"null model");m->reset();return 0; }
    catch(const std::exception& ex) { error=ex.what();return -1; }
}
EXPORT size_t ff_cuda_checkpoint_size(const ff_cuda_model* m) { return m?m->checkpoint_size():0; }
EXPORT int ff_cuda_save(ff_cuda_model* m,uint8_t* output,size_t bytes) {
    try { require(m,"null model");m->save(output,bytes);return 0; }
    catch(const std::exception& ex) { error=ex.what();return -1; }
}
EXPORT int ff_cuda_load(ff_cuda_model* m,const uint8_t* input,size_t bytes) {
    try { require(m,"null model");m->load(input,bytes);return 0; }
    catch(const std::exception& ex) { error=ex.what();return -1; }
}
EXPORT int ff_cuda_probe(uint32_t n,uint64_t edges,const uint64_t* rows,const uint32_t* columns,
                         const Real* weights,const uint8_t* sensory,NeuralParams p,uint32_t steps,
                         const Real* input,Real* v,Real* g,uint8_t* spikes) {
    auto m=ff_cuda_create(n,edges,rows,columns,weights,sensory,p,steps);
    if(!m) return -1;
    int rc=ff_cuda_advance(m,steps,input,v,g,spikes);
    ff_cuda_destroy(m);return rc;
}

#pragma once
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "atomic_checkpoint.hpp"

// Trusted, build-bound state container. Raw CUDA RNG layout is NOT portable.
// FNV detects accidental corruption; it does not authenticate hostile input.
#ifndef FF_CHECKPOINT_BUILD_ID
#error File checkpoint builds must supply a source/toolchain fingerprint
#endif
inline uint64_t photon_checksum(const std::vector<unsigned char>& data) {
    uint64_t value=14695981039346656037ull;
    for(auto byte:data){value^=byte;value*=1099511628211ull;}
    return value;
}
inline void photon_checkpoint(const char* path, bool read,
        std::vector<unsigned char>& data, uint64_t n, uint64_t m,
        uint64_t ticks, uint64_t onset, uint64_t rng_size) {
    std::array<uint64_t,12> expected={0x4650484f544f4e31ull,1,n,m,ticks,onset,
        ticks/2,rng_size,data.size(),CUDART_VERSION,19303,0};
    const std::string identity=FF_CHECKPOINT_BUILD_ID;
    if(identity.size()!=64)throw std::runtime_error("Invalid checkpoint build identity");
    if(read){
        std::ifstream file(path,std::ios::binary);
        std::array<uint64_t,12> header{};std::array<char,64> saved_id{};
        file.read(reinterpret_cast<char*>(header.data()),sizeof(header));
        file.read(saved_id.data(),saved_id.size());
        if(!file || std::memcmp(saved_id.data(),identity.data(),64)!=0)
            throw std::runtime_error("Checkpoint identity/header mismatch");
        for(size_t i=0;i<11;++i)if(header[i]!=expected[i])
            throw std::runtime_error("Checkpoint configuration mismatch");
        file.read(reinterpret_cast<char*>(data.data()),data.size());
        if(!file || file.peek()!=std::char_traits<char>::eof() || photon_checksum(data)!=header[11])
            throw std::runtime_error("Checkpoint length/checksum mismatch");
    }else{
        expected[11]=photon_checksum(data);
        AtomicCheckpoint file(path);
        file.write(expected.data(),sizeof(expected));
        file.write(identity.data(),identity.size());
        file.write(data.data(),data.size());
        file.commit();
    }
}

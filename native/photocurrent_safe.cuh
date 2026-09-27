// Adapted from pinned VisTrans: synchronized warp reduction only.
/*
BSD 3-Clause License

Copyright (c) 2021, FlyBrainLab
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

*/
#include <cuda_runtime.h>
#include <cmath>
using ushort = unsigned short;
static_assert(sizeof(ushort)==2);

#define BLOCK_SIZE 256
#define G_TRP           8       /* conductance of a TRP channel */
#define TRP_REV 0  /* mV */

__inline__ __device__
int warpReduction(volatile int* sdata, int tid){
    int value = sdata[tid] + sdata[tid+32];
    for(int offset=16; offset>0; offset/=2)
        value += __shfl_down_sync(0xffffffffu, value, offset);
    return value;
}

__global__ void
sum_current(ushort2* d_Tstar, int* d_num_microvilli,
            int* d_cum_microvilli,
            double* d_Vm, double* I_all,
            double* I_fb)
{
    int tid = threadIdx.x;
    int bid = blockIdx.x;

    int num_microvilli = d_num_microvilli[bid];
    int shift = d_cum_microvilli[bid];

    int total_open_channel;
    __shared__ int sum[BLOCK_SIZE];
    sum[tid] = 0;

    for(int i = tid; i < num_microvilli; i += BLOCK_SIZE)
        sum[tid] += d_Tstar[i + shift].y;

    __syncthreads();

    if (tid < 64) {
        #pragma unroll
        for(int i = 1; i < BLOCK_SIZE/64; ++i)
            sum[tid] += sum[tid + 64*i];
    }
    __syncthreads();

    if (tid < 32) total_open_channel = warpReduction(sum, tid);

    if (tid == 0) {
        double Vm = (d_Vm[bid]-TRP_REV) * 0.001;
        double I_in;
        if(Vm < 0)
            I_in = total_open_channel * G_TRP * (-Vm);
        else
            I_in = 0;

        I_all[bid] = I_fb[bid] + I_in / 15.7; // convert pA into \muA/cm^2
    }
}

// Adapted pinned VisTrans: warp work index broadcast in registers; reactions unchanged.
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


#include "curand_kernel.h"

extern "C" {
#include "stdio.h"

#define BLOCK_SIZE 128
#define LA 0.5

__device__ __constant__ long long int d_X[5];
__device__ __constant__ int change_ind1[14];
__device__ __constant__ int change1[14];
__device__ __constant__ int change_ind2[14];
__device__ __constant__ int change2[14];


__device__ float num_to_mM(int n)
{
    return n * 5.5353e-4; // n/1806.6;
}

__device__ float mM_to_num(float cc)
{
    return rintf(cc * 1806.6);
}

__device__ float compute_fp( float ca_cc)
{
    float tmp = ca_cc*3.3333333333;
    tmp *= tmp;
    return tmp/(1+tmp);
}

__device__ float compute_fn( float Cstar_cc, float ns)
{
    float tmp = Cstar_cc*5.55555555;
    tmp *= tmp*tmp;
    return ns*tmp/(1+tmp);
}

__device__ float compute_ca(int Tstar, float cstar_cc, float Vm)
{
    float I_in = Tstar*8*fmaxf(-Vm,0);
    float denom = (1060 - 120*cstar_cc + 179.0952 * expf(-39.60793*Vm));
    float numer = I_in * 690.9537 + 0.0795979 + 22*cstar_cc;

    return fmaxf(1.6e-4, numer/denom);
}

__global__ void
transduction(curandStateXORWOW_t *state, float dt, double* d_Vm,
             double* g_ns, double* input,
             int* num_microvilli, int total_microvilli, int* count)
{
    int tid = threadIdx.x;
    int gid = threadIdx.x + blockIdx.x * blockDim.x;
    int wid = tid % 32;
    int wrp = tid >> 5;

    __shared__ int X[BLOCK_SIZE][7];  // number of molecules
    __shared__ float Ca[BLOCK_SIZE];
    __shared__ float fn[BLOCK_SIZE];

    float Vm, ns, lambda;

    float sumrate, dt_advanced;
    int reaction_ind;
    ushort2 tmp;

    // copy random generator state locally to avoid accessing global memory
#ifndef FF_ENTITY_RNG
    curandStateXORWOW_t localstate = state[gid];
#endif


    int start=0;
    if(wid==0) start=atomicAdd(count,32);
    start=__shfl_sync(0xffffffffu,start,0);
    int mid=start+wid;
    int ind;
    while(start < total_microvilli) {
      if(mid < total_microvilli) {
#ifdef FF_ENTITY_RNG
        curandStateXORWOW_t localstate = state[mid];
#endif
        ind = ((ushort*)d_X[4])[mid];
        // load variables that are needed for computing calcium concentration
        tmp = ((ushort2*)d_X[2])[mid];
        X[tid][5] = tmp.x;
        X[tid][6] = tmp.y;

        Vm = d_Vm[ind]*1e-3;
        ns = g_ns[ind];

        // update calcium concentration
        Ca[tid] = compute_ca(X[tid][6], num_to_mM(X[tid][5]), Vm);
        fn[tid] = compute_fn( num_to_mM(X[tid][5]), ns);

        lambda = input[ind]/(double)num_microvilli[ind];

        // load the rest of variables
        tmp = ((ushort2*)d_X[1])[mid];
        X[tid][4] = tmp.y;
        X[tid][3] = tmp.x;
        tmp = ((ushort2*)d_X[0])[mid];
        X[tid][2] = tmp.y;
        X[tid][1] = tmp.x;
        X[tid][0] = ((ushort*)d_X[3])[mid];

        sumrate = lambda + 54198 * Ca[tid] * (0.5 - X[tid][5] * 5.5353e-4) + 5.5 * X[tid][5]; // 11, 12
        sumrate += 25 * (1+10*fn[tid]) * X[tid][6]; // 10
        sumrate += 4 * (1+37.8*fn[tid]) * X[tid][4] ; // 8
        sumrate += (1444+1598.4*fn[tid]) * X[tid][3] ; // 7, 6
        sumrate += (3.7*(1+40*fn[tid]) + 7.05 * X[tid][1]) * X[tid][0] ; // 1, 2
        sumrate += (1560 - 12.6 * X[tid][3]) * X[tid][2]; // 3, 4
        sumrate += 3.5 * (50 - X[tid][2] - X[tid][1] - X[tid][3]) ; // 5
        sumrate += 0.015 * (1+11.5*compute_fp( Ca[tid] )) * X[tid][4]*(X[tid][4]-1)*(25-X[tid][6])*0.5 ; // 9

        dt_advanced = -logf(curand_uniform(&localstate))/(LA+sumrate);

        // If the reaction time is smaller than dt,
        // pick the reaction and update,
        // then compute the total rate and next reaction time again
        // until all dt_advanced is larger than dt.
        // Note that you don't have to compensate for
        // the last reaction time that exceeds dt.
        // The reason is that the exponential distribution is MEMORYLESS.
        while (dt_advanced <= dt) {
            reaction_ind = 0;
            sumrate = curand_uniform(&localstate) * sumrate;

            if (sumrate > 2e-5) {
                sumrate -= lambda;
                reaction_ind = (sumrate<=2e-5) * 13;

                if (!reaction_ind) {
                    sumrate -= mM_to_num(30) * Ca[tid] * (0.5 - num_to_mM(X[tid][5]) );
                    reaction_ind = (sumrate<=2e-5) * 11;

                    if (!reaction_ind) {
                        sumrate -= mM_to_num(5.5) * num_to_mM(X[tid][5]);
                        reaction_ind = (sumrate<=2e-5) * 12;

                        if (!reaction_ind) {
                            sumrate -= 25 * (1+10*fn[tid]) * X[tid][6];
                            reaction_ind = (sumrate<=2e-5) * 10;

                            if (!reaction_ind) {
                                sumrate -= 4 * (1+37.8*fn[tid]) * X[tid][4];
                                reaction_ind = (sumrate<=2e-5) * 8;

                                if (!reaction_ind) {
                                    sumrate -= 144 * (1+11.1*fn[tid]) * X[tid][3];
                                    reaction_ind = (sumrate<=2e-5) * 7;

                                    if (!reaction_ind) {
                                        sumrate -= 3.7*(1+40*fn[tid]) * X[tid][0];
                                        reaction_ind = (sumrate<=2e-5) * 1;

                                        if (!reaction_ind) {
                                            sumrate -= 1300 * X[tid][3];
                                            reaction_ind = (sumrate<=2e-5) * 6;

                                            if (!reaction_ind) {
                                                sumrate -= 3.0 * X[tid][2] * X[tid][3];
                                                reaction_ind = (sumrate<=2e-5) * 4;

                                                if (!reaction_ind) {
                                                    sumrate -= 15.6 * X[tid][2]
                                                        * (100-X[tid][3]);
                                                    reaction_ind = (sumrate<=2e-5) * 3;

                                                    if (!reaction_ind) {
                                                        sumrate -= 3.5 * (50 - X[tid][2]
                                                            - X[tid][1] - X[tid][3]);
                                                        reaction_ind = (sumrate<=2e-5) * 5;

                                                        if(!reaction_ind) {
                                                            sumrate -= 7.05 * X[tid][1]
                                                                * X[tid][0];
                                                            reaction_ind = (sumrate<=2e-5)
                                                                * 2;

                                                            if(!reaction_ind) {
                                                                sumrate -= 0.015 *
                                                                    (1+11.5*compute_fp( Ca[tid] )) * X[tid][4]*(X[tid][4]-1)*(25-X[tid][6])*0.5;
                                                                reaction_ind = (sumrate<=2e-5) * 9;
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            //int ind;

            // only up to two state variables are needed to be updated
            // update the first one.
            ind = change_ind1[reaction_ind];
            X[tid][ind] += change1[reaction_ind];

            //update the second one
            ind = change_ind2[reaction_ind];
            if (ind != 0)
                X[tid][ind] += change2[reaction_ind];

            // compute the advance time again
            Ca[tid] = compute_ca(X[tid][6], num_to_mM(X[tid][5]), Vm);
            fn[tid] = compute_fn( num_to_mM(X[tid][5]), ns );

            sumrate = lambda + 54198*Ca[tid]*(0.5 - X[tid][5]*5.5353e-4)
                + 5.5*X[tid][5]; // 11, 12
            sumrate += 25*(1 + 10*fn[tid])*X[tid][6]; // 10
            sumrate += 4*(1 + 37.8*fn[tid])*X[tid][4]; // 8
            sumrate += (1444 + 1598.4*fn[tid])*X[tid][3]; // 7, 6
            sumrate += (3.7*(1 + 40*fn[tid]) + 7.05*X[tid][1])*X[tid][0]; // 1, 2
            sumrate += (1560 - 12.6*X[tid][3])*X[tid][2]; // 3, 4
            sumrate += 3.5*(50 - X[tid][2] - X[tid][1] - X[tid][3]); // 5
            sumrate += 0.015*(1 + 11.5*compute_fp( Ca[tid] ))
                *X[tid][4]*(X[tid][4] - 1)*(25 - X[tid][6])*0.5; // 9

            dt_advanced -= logf(curand_uniform(&localstate))/(LA+sumrate);

        } // end while

        ((ushort*)d_X[3])[mid] = X[tid][0];
        ((ushort2*)d_X[0])[mid] = make_ushort2(X[tid][1], X[tid][2]);
        ((ushort2*)d_X[1])[mid] = make_ushort2(X[tid][3], X[tid][4]);
        ((ushort2*)d_X[2])[mid] = make_ushort2(X[tid][5], X[tid][6]);

#ifdef FF_ENTITY_RNG
        state[mid] = localstate;
#endif
      }
      if(wid==0) start=atomicAdd(count,32);
      start=__shfl_sync(0xffffffffu,start,0);
      mid=start+wid;
    }
    // copy the updated random generator state back to global memory
#ifndef FF_ENTITY_RNG
    state[gid] = localstate;
#endif
}

}

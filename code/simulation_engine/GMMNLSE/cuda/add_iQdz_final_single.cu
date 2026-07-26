__global__ void add_iQdz_final(float2* A_rmc,
                               const float2* A,
                               const float2* iQdz, const float2* iQdz_2, const float2* iQdz_3,
                               const unsigned int N, const unsigned int M, const unsigned int NUM_MODES) {
    const unsigned int full_thread_idx = threadIdx.x + blockIdx.x*blockDim.x;

    // Calculate the index
    const unsigned int midx = full_thread_idx / N;
    const unsigned int Nidx = full_thread_idx - midx*N;
    

    if (full_thread_idx >= N*NUM_MODES) {
        return;
    }

    const unsigned int max_num_modes = 20;
    __shared__ float2 this_iQdz[max_num_modes*max_num_modes];
    __shared__ float2 this_iQdz_2[max_num_modes*max_num_modes];
    __shared__ float2 this_iQdz_3[max_num_modes*max_num_modes];
    for (int i = 0; i<NUM_MODES*NUM_MODES; i++) {
        this_iQdz[i] = iQdz[i];
        this_iQdz_2[i] = iQdz_2[i];
        this_iQdz_3[i] = iQdz_3[i];
    }
    __syncthreads();

    const unsigned int M2 = M*M;
    const unsigned int M3 = M2*M;

    float2 A_rmc_Ni;
    A_rmc_Ni.x = 0; A_rmc_Ni.y = 0; // initialized
    float2 iQdz_RI;
    unsigned int I = 0;
    // Compute the random mode coupling
    for (int i = 0; i < NUM_MODES; i++) {
        if (i == midx) {
            I = 1;
        } else {
            I = 0;
        }
        iQdz_RI.x = I + M*this_iQdz[i*NUM_MODES+midx].x + M2*this_iQdz_2[i*NUM_MODES+midx].x + M3*this_iQdz_3[i*NUM_MODES+midx].x;
        iQdz_RI.y = M*this_iQdz[i*NUM_MODES+midx].y + M2*this_iQdz_2[i*NUM_MODES+midx].y + M3*this_iQdz_3[i*NUM_MODES+midx].y;

        A_rmc_Ni.x += (iQdz_RI.x*A[Nidx+i*N].x - iQdz_RI.y*A[Nidx+i*N].y);
        A_rmc_Ni.y += (iQdz_RI.x*A[Nidx+i*N].y + iQdz_RI.y*A[Nidx+i*N].x);
    }
    A_rmc[Nidx+midx*N] = A_rmc_Ni;
}
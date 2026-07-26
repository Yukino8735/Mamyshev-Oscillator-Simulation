__global__ void add_iQdz(double2* A_rmc,
                         const double2* A,
                         const double2* iQdz, const double2* iQdz_2, const double2* iQdz_3,
                         const unsigned int N, const unsigned int M, const unsigned int NUM_MODES) {
    const unsigned int full_thread_idx = threadIdx.x + blockIdx.x*blockDim.x;

    // Calculate the index
    const unsigned int NM = N*M;
    const unsigned int midx = full_thread_idx /NM;
    const unsigned int tmp = full_thread_idx - midx*NM;
    const unsigned int Midx = tmp / N;
    const unsigned int Nidx = tmp - Midx*N;

    if (full_thread_idx >= NM*NUM_MODES) {
        return;
    }

    const unsigned int max_num_modes = 20;
    __shared__ double2 this_iQdz[max_num_modes*max_num_modes];
    __shared__ double2 this_iQdz_2[max_num_modes*max_num_modes];
    __shared__ double2 this_iQdz_3[max_num_modes*max_num_modes];
    for (int i = 0; i<NUM_MODES*NUM_MODES; i++) {
        this_iQdz[i] = iQdz[i];
        this_iQdz_2[i] = iQdz_2[i];
        this_iQdz_3[i] = iQdz_3[i];
    }
    __syncthreads();

    const unsigned int Midx2 = Midx*Midx;
    const unsigned int Midx3 = Midx2*Midx;

    double2 A_rmc_NiMi;
    A_rmc_NiMi.x = 0; A_rmc_NiMi.y = 0; // initialized
    double2 iQdz_RI;
    unsigned int I = 0;
    // Compute the random mode coupling
    for (int i = 0; i < NUM_MODES; i++) {
        if (i == midx) {
            I = 1;
        } else {
            I = 0;
        }
        iQdz_RI.x = I + Midx*this_iQdz[i*NUM_MODES+midx].x + Midx2*this_iQdz_2[i*NUM_MODES+midx].x + Midx3*this_iQdz_3[i*NUM_MODES+midx].x;
        iQdz_RI.y = Midx*this_iQdz[i*NUM_MODES+midx].y + Midx2*this_iQdz_2[i*NUM_MODES+midx].y + Midx3*this_iQdz_3[i*NUM_MODES+midx].y;

        A_rmc_NiMi.x += (iQdz_RI.x*A[Nidx+Midx*N+i*NM].x - iQdz_RI.y*A[Nidx+Midx*N+i*NM].y);
        A_rmc_NiMi.y += (iQdz_RI.x*A[Nidx+Midx*N+i*NM].y + iQdz_RI.y*A[Nidx+Midx*N+i*NM].x);
    }
    A_rmc[Nidx+Midx*N+midx*NM] = A_rmc_NiMi;
}
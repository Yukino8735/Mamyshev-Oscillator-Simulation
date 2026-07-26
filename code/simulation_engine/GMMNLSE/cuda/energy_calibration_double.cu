__global__ void energy_calibration(double2* A_calibrated, const double2* Ao, const double2* Ai, const unsigned int N, const unsigned int M, const unsigned int NUM_MODES) {
    const unsigned int full_thread_idx = threadIdx.x + blockIdx.x*blockDim.x;

    // Calculate the index
    const unsigned int NM = N*M;
    const unsigned int Midx = full_thread_idx / N;
    const unsigned int Nidx = full_thread_idx - Midx*N;
    

    if (full_thread_idx >= NM) {
        return;
    }

    double Ao_NiMi = 0, Ai_NiMi = 0;
    // Compute the random mode coupling
    for (int i = 0; i < NUM_MODES; i++) {
        Ao_NiMi += (pow(Ao[Nidx+Midx*N+i*NM].x,2) + pow(Ao[Nidx+Midx*N+i*NM].y,2));
        Ai_NiMi += (pow(Ai[Nidx+Midx*N+i*NM].x,2) + pow(Ai[Nidx+Midx*N+i*NM].y,2));
    }

    if (abs(Ai_NiMi/Ao_NiMi - 1) < 0.1) { // ignore possible NaN or inf
        for (int i = 0; i < NUM_MODES; i++) {
            A_calibrated[Nidx+Midx*N+i*NM].x = Ao[Nidx+Midx*N+i*NM].x*sqrt(Ai_NiMi/Ao_NiMi);
            A_calibrated[Nidx+Midx*N+i*NM].y = Ao[Nidx+Midx*N+i*NM].y*sqrt(Ai_NiMi/Ao_NiMi);
        }
    }
}
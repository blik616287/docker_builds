/**
 * mpi_matrix_multiply.c
 * 
 * A simple MPI program to perform distributed matrix multiplication.
 * 
 * Compile with: mpicc -o mpi_matrix_multiply mpi_matrix_multiply.c
 * Run with: mpirun -np <processes> ./mpi_matrix_multiply
 */

#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include <time.h>
#include <string.h>

#define MATRIX_SIZE 1000  // Size of the square matrices

void initialize_matrix(double *matrix, int size) {
    for (int i = 0; i < size * size; i++) {
        matrix[i] = (double)rand() / RAND_MAX;
    }
}

void print_matrix_info(const char *name, double *matrix, int size) {
    double sum = 0.0;
    for (int i = 0; i < size * size; i++) {
        sum += matrix[i];
    }
    printf("%s: size=%dx%d, sum=%f\n", name, size, size, sum);
}

int main(int argc, char *argv[]) {
    int rank, world_size, rows_per_proc;
    double *a = NULL, *b = NULL, *c = NULL;
    double *a_local = NULL, *c_local = NULL;
    double start_time, end_time;
    char hostname[256];
    // Initialize MPI
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);
    // Get hostname for logging
    gethostname(hostname, sizeof(hostname));
    printf("Process %d/%d running on %s\n", rank, world_size, hostname);
    // Calculate how many rows each process will handle
    rows_per_proc = MATRIX_SIZE / world_size;
    // Allocate memory for local portions
    a_local = (double *)malloc(rows_per_proc * MATRIX_SIZE * sizeof(double));
    b = (double *)malloc(MATRIX_SIZE * MATRIX_SIZE * sizeof(double));
    c_local = (double *)malloc(rows_per_proc * MATRIX_SIZE * sizeof(double));
    if (!a_local || !b || !c_local) {
        fprintf(stderr, "Process %d: Memory allocation failed\n", rank);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    // Process 0 initializes the matrices
    if (rank == 0) {
        printf("Matrix multiplication: %d x %d matrices with %d processes\n", 
               MATRIX_SIZE, MATRIX_SIZE, world_size);
        // Allocate memory for full matrices
        a = (double *)malloc(MATRIX_SIZE * MATRIX_SIZE * sizeof(double));
        c = (double *)malloc(MATRIX_SIZE * MATRIX_SIZE * sizeof(double));
        if (!a || !c) {
            fprintf(stderr, "Process 0: Memory allocation for full matrices failed\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        // Initialize matrices with random values
        srand(time(NULL));
        initialize_matrix(a, MATRIX_SIZE);
        initialize_matrix(b, MATRIX_SIZE);
        // Print matrix info
        print_matrix_info("Matrix A", a, MATRIX_SIZE);
        print_matrix_info("Matrix B", b, MATRIX_SIZE);
    }
    // Start timing
    start_time = MPI_Wtime();
    // Distribute matrix A row-wise to all processes
    MPI_Scatter(a, rows_per_proc * MATRIX_SIZE, MPI_DOUBLE,
                a_local, rows_per_proc * MATRIX_SIZE, MPI_DOUBLE,
                0, MPI_COMM_WORLD);
    // Broadcast matrix B to all processes
    MPI_Bcast(b, MATRIX_SIZE * MATRIX_SIZE, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    // Each process computes its portion of the result
    printf("Process %d: Computing %d rows\n", rank, rows_per_proc);
    for (int i = 0; i < rows_per_proc; i++) {
        for (int j = 0; j < MATRIX_SIZE; j++) {
            c_local[i * MATRIX_SIZE + j] = 0.0;
            for (int k = 0; k < MATRIX_SIZE; k++) {
                c_local[i * MATRIX_SIZE + j] +=
                    a_local[i * MATRIX_SIZE + k] * b[k * MATRIX_SIZE + j];
            }
        }
    }
    // Gather results back to process 0
    MPI_Gather(c_local, rows_per_proc * MATRIX_SIZE, MPI_DOUBLE,
               c, rows_per_proc * MATRIX_SIZE, MPI_DOUBLE,
               0, MPI_COMM_WORLD);
    // End timing
    end_time = MPI_Wtime();
    // Process 0 prints the results
    if (rank == 0) {
        printf("Computation completed in %f seconds\n", end_time - start_time);
        print_matrix_info("Result Matrix C", c, MATRIX_SIZE);
        // Free full matrices
        free(a);
        free(c);
    }
    // Free local portions
    free(a_local);
    free(b);
    free(c_local);
    MPI_Finalize();
    return 0;
}

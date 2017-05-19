/*
 * Genetic Algorithm: Meals and the Knapsack Problem
 *
 * Approximate balanced meals using genetic algorithm
 *
 * Owen Cummings (ocummings) and Alex Qian-Wang (alexqw)
 */

#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include <assert.h>
#include <math.h>
#include <string.h>
#include <time.h>
#include "RNG/rng_code.h"
#include "gene_pool.h"
#include "algorithm.h"
#include "test_genetic_algorithm.h"


/* solve: iterate through multiple generations from a starting
 * gene_pool
 *
 * random_t random: handle for random number generator
 * gene_pool_t gene_pool: initial gene pool
 * wt_val_coef_t wt_val_coef: coefficients for value/weight functions
 * int num_gens: number of generations to run
 * double max_cal: maximum number of calories allowed in a meal
 * int max_surv: maximum number of survivors per generation
 *
 * returns: gene with maximum value
 */

int *solve(random_t random, gene_pool_t gene_pool, wt_val_coef_t wt_val_coef, int num_gens, double max_cal, int max_surv) {
    for (int i=0; i < num_gens; i++) {
        gene_pool = insert(gene_pool, wt_val_coef, max_cal, max_surv);
        gene_pool = reproduce(random, gene_pool);
    }
    double best_value = 0.0;
    int *best_gene = malloc((gene_pool->m)*sizeof(int));
    for (int j=0; j < gene_pool->n; j++) {
        int *curr_gene = gene_pool->genes[j];
        double calories = compute_meal_calories(wt_val_coef->cals_coef, curr_gene, gene_pool->m);
        if (calories <= max_cal) {
            double nutrition = compute_meal_value(wt_val_coef, curr_gene);
            if (nutrition > best_value) {
                best_value = nutrition;
                best_gene = curr_gene;
            }
        }
    }
    int *rv = duplicate_gene(best_gene, gene_pool->m);
    free(best_gene);
    return rv;
}

/* insert: insert survivors into a new gene pool using insertion sort
 *
 * returns: new gene pool
 */

gene_pool_t insert(gene_pool_t old_gene_pool, wt_val_coef_t wt_val_coef, double max_cal, int max_surv) {
    int n = old_gene_pool->n;
    int m = old_gene_pool->m;
    gene_pool_t new_gene_pool = mk_empty_gene_pool(n, m);
    for (int i=0; i < n; i++) {
        int *curr_old_gene = old_gene_pool->genes[i];
        double calories = compute_meal_calories(wt_val_coef->cals_coef, curr_old_gene, m);
        if (calories <= max_cal) {
            double old_nutrition = compute_meal_value(wt_val_coef, curr_old_gene);
            for (int j=0; j < n; j++) {
                int *curr_new_gene = new_gene_pool->genes[j];
                if (curr_new_gene == NULL) {
                    new_gene_pool->genes[j] = curr_old_gene;
                    break;
                }
                else {
                    double new_nutrition = compute_meal_value(wt_val_coef, curr_new_gene);
                    if (old_nutrition > new_nutrition) {
                        gene_pool_t duplicate_old_pool = duplicate_gene_pool(old_gene_pool);
                        new_gene_pool = pointer_mover(duplicate_old_pool->genes[i], new_gene_pool, j);
                        break;
                    }
                }
            }
        }
    }
    for (int k=max_surv; k < n; k++) {
        new_gene_pool->genes[k] = NULL;
    }
    return new_gene_pool;
}

/* pointer_mover: reorganize pointers below the insertion point and inserts the survivor
 *
 * returns: new gene pool
 */

gene_pool_t pointer_mover(int *survivor, gene_pool_t gene_pool, int insertion_point) {
    int n = gene_pool->n;
    int m = gene_pool->m;
    gene_pool_t rv_pool = mk_empty_gene_pool(n, m);
    for (int i=insertion_point; i+1 < n; i++) {
        rv_pool->genes[i+1] = gene_pool->genes[i];
    }
    int *last_array = gene_pool->genes[n-1];
    if (last_array != NULL) {
        free(last_array);
        last_array = NULL;
    }
    rv_pool->genes[insertion_point] = survivor;
    for (int j=0; j < insertion_point; j++) {
        rv_pool->genes[j] = gene_pool->genes[j];
    }
    return rv_pool;
}

/* reproduce: perform crossover on survivors and mutation on children;
 * add children to the specified gene pool until the pool is full.
 *
 * returns: the gene pool
 */

gene_pool_t reproduce(random_t random, gene_pool_t gene_pool){
    int n = gene_pool->n;
    int m = gene_pool->m;
    if (gene_pool->genes[1] == NULL) {
        printf("ERROR: Need at least two survivors to continue!\n");
        exit(0);
    }
    int num_survivors = 0;
    for (int i=0; i < n; i++) {
        if (gene_pool->genes[i] != NULL) {
            num_survivors++;
        }
    }
    for (int j = num_survivors; j < n; j++) {
        int parent1 = 0;
        int parent2 = 0;
        while (parent2 == parent1) {
            parent1 = rand_range(random, num_survivors);
            parent2 = rand_range(random, num_survivors);
        }
        int *babby = crossover_and_choose(random, gene_pool->genes[parent1], gene_pool->genes[parent2], m);
        babby = mutate(random, babby, m, m);
        gene_pool->genes[j] = babby;
    }
    gene_pool_t rv = duplicate_gene_pool(gene_pool);
    return rv;
}

/* crossover_and_choose: performs crossover by switching middle
 * elements and then chooses a child uniformly at random
 *
 * returns: single gene
 */

int *crossover_and_choose(random_t random, int *first_parent, int *second_parent, int m) {
    int low_cross = m / 3 - 1;
    int high_cross = 2 * (m / 3);
    int *duplicate1 = duplicate_gene(first_parent, m);
    int *duplicate2 = duplicate_gene(second_parent, m);
    int i = 0;
    while (i < m) {
        if ((i > low_cross) && (i < high_cross)) {
            duplicate1[i] = second_parent[i];
            duplicate2[i] = first_parent[i];
        }
        i++;
    }
    if (rand_bool(random, 2)) {
        return duplicate1;
    }
    else {
        return duplicate2;
    }
}

/* mutate perform mutation on a gene sequence given a probability of
 * mutation
 *
 * returns: the mutated gene
 */

int *mutate(random_t random, int *single_gene, int m, int prob){
    int i = 0;
    while (i < m) {
        if (rand_bool(random, prob)) {
            if (single_gene[i] == 0) {
                single_gene[i] = 1;
            }
            else {
                single_gene[i] = 0;
            }
        }
        i = i + 1;
    }
    return single_gene;
}

/* compute_meal_calories: compute total the number of calories
 * associated with a meal (a single gene sequence)
 *
 * returns: total number of calories
 */

double compute_meal_calories(double *cals_coef, int *single_gene, int m) {
    int i = 0;
    double total = 0;
    while (i < m) {
        total = total + cals_coef[i]*single_gene[i];
        i = i + 1;
    }
    return total;
}

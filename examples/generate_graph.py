import json
import random
from collections import defaultdict

from helpers import generate_payloads


def generate_full_graph():
    # N_nodes = (N_parents * (N_children + 1)) * (N_ids + 1)
    # N_HasVersion = N_parents * N_children
    # N_IsIdenticalTo = N_nodes
    # N_Cites = ~ N_parents * N_citations

    N_parents = 10000
    N_children = 5
    N_ids = 2
    N_citations = 20

    relations = []
    parents = ['P_' + str(i) for i in range(N_parents)]
    par_group = defaultdict(lambda: [])
    child_lut = {}
    for p in parents:
        for id_idx in range(N_ids):
            p_iden = p + "_ID_" + str(id_idx)
            par_group[p].append(p_iden)
            relations.append(['C', p, 'IsIdenticalTo', p_iden, '2018-01-01'])

        for c_idx in range(N_children):
            c = p + "_C_" + str(c_idx)
            par_group[p].append(p)
            relations.append(['C', p, 'HasVersion', c, '2018-01-01'])

            for id_idx in range(N_ids):
                c_iden = c + "_ID_" + str(id_idx)
                par_group[p].append(c_iden)
                relations.append(['C', c, 'IsIdenticalTo', c_iden, '2018-01-01'])

    for idx, (par, grp) in enumerate(par_group.items()):
        if (idx + 1) <= N_parents - 1:
            n_samples = min(N_citations, N_parents - idx - 1)
            next_parents = random.sample(range(idx + 1, N_parents), n_samples)
            for next_par_idx in next_parents:
                citeA = random.choice(grp)
                next_par = parents[next_par_idx]
                citeB = random.choice(par_group[next_par])
                relations.append(['C', citeA, 'Cites', citeB, '2018-01-01'])

    res = generate_payloads([relations])
    print(json.dumps(res, indent=2))


def cite_by_all(parent_idx):
    # N_nodes = (N_parents * (N_children + 1)) * (N_ids + 1)
    # N_HasVersion = N_parents * N_children
    # N_IsIdenticalTo = N_nodes
    # N_Cites = ~ N_parents * N_citations

    N_parents = 10000
    N_children = 5
    N_ids = 2
    N_citations = 20

    relations = []
    parents = ['P_' + str(i) for i in range(N_parents)]
    par_group = defaultdict(lambda: [])
    child_lut = {}
    for p in parents:
        for id_idx in range(N_ids):
            p_iden = p + "_ID_" + str(id_idx)
            par_group[p].append(p_iden)
            #relations.append(['C', p, 'IsIdenticalTo', p_iden, '2018-01-01'])

        for c_idx in range(N_children):
            c = p + "_C_" + str(c_idx)
            par_group[p].append(p)
            #relations.append(['C', p, 'HasVersion', c, '2018-01-01'])

            for id_idx in range(N_ids):
                c_iden = c + "_ID_" + str(id_idx)
                par_group[p].append(c_iden)
                #relations.append(['C', c, 'IsIdenticalTo', c_iden, '2018-01-01'])

    for idx, (par, grp) in enumerate(par_group.items()):
        if (idx + 1) <= N_parents - 1:
            next_parents = [parent_idx,]
            for next_par_idx in next_parents:
                citeA = random.choice(grp)
                next_par = parents[next_par_idx]
                citeB = random.choice(par_group[next_par])
                relations.append(['C', citeA, 'Cites', citeB, '2018-01-01'])

    res = generate_payloads([relations])
    print(json.dumps(res, indent=2))


if __name__ == '__main__':
    ## Generates a 10k object, 20k citations graph
    ## (180k identifiers, 380k relations)
    # generate_full_graph()

    ## Create 10k citaions to a single parent's group with ID 9999's
    cite_by_all(9999)

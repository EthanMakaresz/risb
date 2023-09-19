import numpy as np
import unittest
from itertools import product

from risb.embedding import EmbeddingAtomDiag
from triqs.operators import Operator, n, c_dag, c
from triqs.operators.util.observables import S2_op, N_op

def solve(spin_names, n_orb, h_loc, Lambda_c, D):
    gf_struct = [ (bl, n_orb) for bl in ['up', 'dn'] ]
    embedding = EmbeddingAtomDiag(h_loc, gf_struct)
    embedding.set_h_emb(Lambda_c, D)
    embedding.solve()
    Nf = dict()
    Mcf = dict()
    Nc = dict()
    for bl, bl_size in gf_struct:
        Nf[bl] = embedding.get_nf(bl)
        Mcf[bl] = embedding.get_mcf(bl)
        Nc[bl] = embedding.get_nc(bl)
    NOp = N_op(spin_names, n_orb, off_diag=True)
    S2Op = S2_op(spin_names, n_orb, off_diag=True)
    return Nf, Mcf, Nc, embedding.gs_energy, embedding.overlap(NOp), embedding.overlap(S2Op)

class tests(unittest.TestCase):

    def test_one_band(self):
        U = 1
        mu = U / 2.0 # half-filling
        n_orb = 1
        spin_names = ['up', 'dn']
        h_loc = U * n('up', 0) * n('dn', 0)
        Lambda_c = dict()
        D = dict()
        for bl in spin_names:
            Lambda_c[bl] = np.array([ [ -mu ] ])
            D[bl] = np.array([ [ -0.3333 ] ])
        Nf, Mcf, Nc, gs_energy, N, S2 = solve(spin_names, n_orb, h_loc, Lambda_c, D)
                
        Nf_expected = np.array([[0.5]])
        Mcf_expected = np.array([[0.4681588161332029]])
        Nc_expected = np.array([[0.5]])
        gs_energy_expected = -0.9619378905494498
        N_expected = 1.0
        S2_expected = 0.5066828353209953
        for bl in spin_names:
            np.testing.assert_allclose(Nf_expected, Nf[bl], rtol=0, atol=1e-12)
            np.testing.assert_allclose(Mcf_expected, Mcf[bl], rtol=0, atol=1e-12)
            np.testing.assert_allclose(Nc_expected, Nc[bl], rtol=0, atol=1e-12)
        assert(np.abs(gs_energy - gs_energy_expected) < 1e-12)
        assert(np.abs(N - N_expected) < 1e-12)
        assert(np.abs(S2 - S2_expected) < 1e-12)

    def test_bilayer(self):
        U = 1
        V = 0.25
        J = 0
        mu = U / 2.0 # half-filling
        n_orb = 2
        spin_names = ['up','dn']
        h_loc = Operator()
        for o in range(n_orb):
            h_loc += U * n("up",o) * n("dn",o)
        for s in spin_names:
            h_loc += V * ( c_dag(s,0)*c(s,1) + c_dag(s,1)*c(s,0) )
        for s1,s2 in product(spin_names,spin_names):
            h_loc += 0.5 * J * c_dag(s1,0) * c(s2,0) * c_dag(s2,1) * c(s1,1)
        Lambda_c = dict()
        D = dict()
        for bl in spin_names:
            Lambda_c[bl] = np.array([ [ -mu        , -0.00460398 ],
                                      [-0.00460398, -mu         ] ])
            D[bl] = np.array([ [ -2.59694448e-01, 0               ],
                               [ 0              , -2.59694448e-01 ] ])
        Nf, Mcf, Nc, gs_energy, N, S2 = solve(spin_names, n_orb, h_loc, Lambda_c, D)
        
        Nf_expected = np.array([ [ 0.5                , -0.1999913941210893 ],
                                 [ -0.1999913941210893, 0.5                 ] ])
        Mcf_expected = np.array([ [ 0.42326519677453511, 0                   ],
                                  [ 0,                   0.42326519677453511 ] ])
        Nc_expected = np.array([ [ 0.5                , -0.1836332097072352 ],
                                 [ -0.1836332097072352, 0.5                 ] ])
        gs_energy_expected = -1.7429249197415944
        N_expected = 2.0
        S2_expected = 0.8247577338845973
        for bl in spin_names:
            np.testing.assert_allclose(Nf_expected, Nf[bl], rtol=0, atol=1e-12)
            np.testing.assert_allclose(Mcf_expected, Mcf[bl], rtol=0, atol=1e-12)
            np.testing.assert_allclose(Nc_expected, Nc[bl], rtol=0, atol=1e-12)
        assert(np.abs(gs_energy - gs_energy_expected) < 1e-12)
        assert(np.abs(N - N_expected) < 1e-12)
        assert(np.abs(S2 - S2_expected) < 1e-12)

    def test_dh_trimer(self):
        # At two-thirds filling
        U = 1
        tk = 1
        n_orb = 3
        spin_names = ['up','dn']
        gf_struct = [ (bl, n_orb) for bl in ['up', 'dn'] ]

        def hubb_N(tk, U, n_orb, spin_names):
            phi = 2.0 * np.pi / n_orb
            h_loc = Operator()
            # hopping
            for a,m,mm,s in product(range(n_orb),range(n_orb),range(n_orb), spin_names):
                h_loc += (-tk / n_orb) * c_dag(s,m) * c(s,mm) * np.exp(-1j * phi * a * m) * np.exp(1j * phi * np.mod(a+1,n_orb) * mm)
                h_loc += (-tk / n_orb) * c_dag(s,m) * c(s,mm) * np.exp(-1j * phi * np.mod(a+1,n_orb) * m) * np.exp(1j * phi * a * mm)
            # hubbard U
            for m,mm,mmm in product(range(n_orb),range(n_orb),range(n_orb)):
                h_loc += (U / n_orb) * c_dag("up",m) * c("up",mm) * c_dag("dn",mmm) * c("dn",np.mod(m+mmm-mm,n_orb))
            return h_loc.real
        h_loc = hubb_N(tk, U, n_orb, spin_names)
        Lambda_c = dict()
        D = dict()
        for bl in spin_names:
            Lambda_c[bl] = np.array([ [ -1.91730088, -0.        , -0.         ],
                                      [ -0.        , -1.69005946, -0.         ],
                                      [ -0.        , -0.        , -1.69005946 ] ])
            D[bl] = np.array([ [ -0.26504931,  0.        ,  0.        ],
                               [ 0.        , -0.39631238,  0.         ],
                               [ 0.        ,  0.        , -0.39631238 ] ])
        Nf, Mcf, Nc, gs_energy, N, S2 = solve(spin_names, n_orb, h_loc, Lambda_c, D)
        
        Nf_expected = np.array([ [ 0.9932309740187902, 0.                , 0.                 ],
                                 [ 0.                , 0.5033842231804342, 0.                 ],
                                 [ 0.                , 0.                , 0.5033842231804342 ] ])
        Mcf_expected = np.array([ [ 0.0811187181751014, 0.                , 0.                 ],
                                  [ 0.                , 0.4910360103357626, 0.                 ],
                                  [ 0.                , 0.                , 0.4910360103357626 ] ])
        Nc_expected = np.array([ [ 0.9909259681893234, 0.                , 0.                ],
                                 [ 0.                , 0.5045367260951683, 0.                ],
                                 [ 0.                , 0.                , 0.5045367260951683] ])
        gs_energy_expected = -9.555511743344764
        N_expected = 3.99999884075932
        S2_expected = 0.9171025003755656
        for bl in spin_names:
            np.testing.assert_allclose(Nf_expected, Nf[bl], rtol=0, atol=1e-12)
            np.testing.assert_allclose(Mcf_expected, Mcf[bl], rtol=0, atol=1e-12)
            np.testing.assert_allclose(Nc_expected, Nc[bl], rtol=0, atol=1e-12)
        assert(np.abs(gs_energy - gs_energy_expected) < 1e-12)
        assert(np.abs(N - N_expected) < 1e-12)
        assert(np.abs(S2 - S2_expected) < 1e-12)
if __name__ == '__main__':
    unittest.main()
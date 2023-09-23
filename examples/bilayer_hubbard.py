import numpy as np

from triqs.lattice.tight_binding import TBLattice, BravaisLattice, BrillouinZone, MeshBrZone
from triqs.operators import Operator, c_dag, c, n
from triqs.operators.util.op_struct import set_operator_structure
from triqs.operators.util.observables import S2_op, N_op

from risb import LatticeSolver
from risb.kweight import SmearingKWeight
from risb.embedding import EmbeddingAtomDiag

# Number of orbitals and spin structure
n_orb = 2
spin_names = ['up','dn']
gf_struct = set_operator_structure(spin_names, n_orb, off_diag=True)

# Non-interacting cubic dispersion on lattice, built using TRIQS
nkx = 10 # nkx**3 total number of k-points
t = - 1.0 / 3.0 # hopping amplitude
units = np.eye(3) # lattice vectors, a1, a2, a3 on a cube
hoppings = {}
for i in range(3):
    hoppings[ tuple((units[:,i]).astype(int)) ] = np.eye(n_orb) * t
    hoppings[ tuple((-units[:,i]).astype(int)) ] = np.eye(n_orb) * t
tbl = TBLattice(units=units, hoppings=hoppings, orbital_positions=[(0,0,0)]*n_orb)
bl = BravaisLattice(units=units)
bz = BrillouinZone(bl)
mk = MeshBrZone(bz, nkx)
h0_k = dict()
for bl, _ in gf_struct:
    h0_k[bl] = tbl.fourier(mk).data

# Hubbard interactions    
U = 4 # Hubbard
V = 0.25 # Bilayer hopping
h_int = Operator()
for o in range(n_orb):
    h_int += U * n("up",o) * n("dn",o)
h0_loc = Operator()
for s in spin_names:
    h0_loc += V * ( c_dag(s,0)*c(s,1) + c_dag(s,1)*c(s,0) )
h_loc = h0_loc + h_int

# Set up class to work out k-space integration weights
beta = 40 # inverse temperature
n_target = 2 # half-filling
kweight = SmearingKWeight(beta=beta, n_target=n_target)
# or fix mu = U/2 -> kweight = SmearingKWeight(beta=beta, mu=mu)

# (Optional) set up function to symmetrize mean-field matrices
#def symmetries(A):
#    n_clusters = len(A)
#    A_sym = [0 for i in range(n_clusters)]
#    for i in range(n_clusters):
#        for bl in A[i]:
#            A_sym[i] += A[i][bl] / len(A[i])
#        for bl in A[i]:
#            A[i][bl] = A_sym[i]
#    return A

# Set up class to solve embedding problem
embedding = EmbeddingAtomDiag(h_loc, gf_struct)

# Setup RISB solver class  
# gf_struct and embedding must be for each cluster. In this case
# there is only one cluster, so a list with one cluster is passed.
S = LatticeSolver(h0_k=h0_k,
                  gf_struct=[gf_struct],
                  embedding=[embedding],
                  update_weights=kweight.update_weights)
                  #symmetries=[symmetries])

# (Optional) Initialize R and Lambda matrices
#for bl, bl_size in gf_struct:
#    np.fill_diagonal(S.R[bl], 1)
#    np.fill_diagonal(S.Lambda[bl], 0)

# Solve
S.solve(tol=1e-6)
 
# Average number of particles on a cluster
NOp = N_op(spin_names, n_orb, off_diag=True)
N = embedding.overlap(NOp)

# Effective total spin of a cluster
S2Op = S2_op(spin_names, n_orb, off_diag=True)
S2 = embedding.overlap(S2Op)

# Print out some interesting observables
with np.printoptions(formatter={'float': '{: 0.4f}'.format}):
    for i in range(S.n_clusters):
        for bl, Z in S.Z[i].items():
            print(f"Quasiaprticle weight Z[{bl}] = \n{Z}")
        for bl, Lambda in S.Lambda[i].items():
            print(f"Correlation potential Lambda[{bl}] = \n{Lambda}")
        print(f"Number of partices per cluster N = \n{N:0.4f}")
        print(f"Effective spin of a cluster S = \n{(0.5 * np.sqrt(4 * (S2 + 1)) - 1):0.4f}")

import numpy as np
from scipy.optimize import brentq

class SmearingKWeight:
    """
    Obtain weights for k-space integrals using smearing functions.

    Parameters
    ----------

    beta : float
        Inverse temperature

    mu : optional, float
        Chemical potential. One of mu or n_target needs to be provided.

    n_target : optional, float
        Target lattice filling per unit cell. One of mu or n_target needs to be provided.
    
    """
    
    def __init__(self, beta, mu=None, n_target=None, method='fermi'):
        self._beta = beta
        self._mu = mu
        self._n_target = n_target
        
        if method == 'fermi':
            self.smear_function = self.fermi
        elif method == 'gaussian':
            self.smear_function = self.gaussian
        elif method == 'methfessel-paxton':
            self.smear_function = self.methfessel_paxton
        else:
            raise ValueError('Unrecoganized smearing function !')
        
    @staticmethod
    def fermi(energies, beta, mu):
        e = energies - mu
        return np.exp(-beta*e*(e > 0))/(1 + np.exp(-beta*np.abs(e)))
    
    @staticmethod
    def gaussian(energies, beta, mu):
        from scipy.special import erfc
        return 0.5 * erfc( beta * (energies - mu) )

    @staticmethod    
    def methfessel_paxton(energies, beta, mu, N=1):
        from scipy.special import erfc
        from scipy.special import factorial
        from scipy.special import hermite
        def A_n(n):
            return (-1)**n / ( factorial(n) * 4**n * np.sqrt(np.pi) )
        
        x = beta * (energies - mu)
        
        S = 0.5 * erfc(x) # S_0
        for n in range(1,N+1):
            H_n = hermite(2*n-1)
            S += A_n(n) * H_n(x) * np.exp(-x**2)
        return S
    
    def update_energies(self, energies):
        self._energies = energies
        self.update_n_k()
        return self.energies
    
    def update_n_k(self):
        if isinstance(self._energies, dict):
            first_key = next(iter(self._energies))
            self._n_k = self._energies[first_key].shape[0]
            for en in self._energies.values():
                if self.n_k != en.shape[0]:
                    # FIXME Must they? I don't see why, but its weird to not
                    raise ValueError('Blocks must be on the same sized grid !')
        else:
            self._n_k = self._energies.shape[0]
        return self.n_k
    
    def update_mu(self):
        # Standard brentq, but for transparancy copied from github.com/TRIQS/hartree_fock
        e_min = np.inf
        e_max = -np.inf
        for en in self.energies.values():
            bl_min = en.min()
            bl_max = en.max()
            if bl_min < e_min:
                e_min = bl_min
            if bl_max > e_max:
                e_max = bl_max
            
        def target_function(mu):
            n = 0
            for en in self.energies.values():
                n += np.sum(self.smear_function(en, self.beta, mu)) / self.n_k
            return n - self.n_target
        self._mu = brentq(target_function, e_min, e_max)
        return self.mu

    def update_weights(self, energies):
        """
        Update the integral weighting factors at each k-point.

        Parameters
        ----------

        energies : dict of arrays
            Energies at each k-point. Each key in dictionary is a different
            symmetry block, and its associated value is a list of energies.

        """
        self.update_energies(energies)
        if self._n_target is not None:
            self.update_mu()

        self._weight = dict()
        for bl in self.energies:
            self._weight[bl] = self.smear_function(self.energies[bl], self.beta, self.mu) / self.n_k
        return self._weight    
    
    @property
    def beta(self):
        return self._beta
    
    @property
    def mu(self):
        return self._mu
    
    @property
    def n_target(self):
        return self._n_target
    
    @property
    def energies(self):
        return self._energies
    
    @property
    def n_k(self):
        return self._n_k
    
    @property
    def weights(self):
        return self._weights
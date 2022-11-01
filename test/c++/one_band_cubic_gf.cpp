#include "./common.hpp"

TEST(one_band_cubic_gf, half_filling) { // NOLINT

  using namespace risb::functions;
  using namespace risb::embedding_atom_diag;
  
  double const beta = 10; // inverse temperature
  int const nw = 10*beta; // number of matsubara frequencies
  int const nkx = 6; // k pts in each dimension
  
  std::vector<std::string> const spin_names = {"up","dn"};
  auto const gf_struct = gf_struct_t{{"up", {1}}, {"dn", {1}}};
  
  double const U = 0.5;
  auto const h_loc = U * n("up", 1) * n("dn", 1);
  double const mu = U / 2.0; // half-filling

  auto [R, lambda] = build_mf_matrices(gf_struct);
  auto [D, lambda_c] = build_mf_matrices(gf_struct);
  
  auto const g0 = build_g0_k_z_cubic(nw, nkx, beta); // first guess for g_k_iw
  auto g0_vec = std::vector{g0, g0};
  auto const g0_k_iw = block_gf{g0_vec};
  auto g_iw = block_gf<imfreq>{{beta, Fermion, nw}, gf_struct};
  auto g0_iw(g_iw);

  // gf meshes
  auto const &k_mesh = std::get<0>(g0.mesh());
  auto const &iw_mesh = std::get<1>(g0.mesh());
    
  auto emb_solver = embedding_atom_diag<false>(gf_struct);
 
  double error;
  int total_cycles = 0;
  
  int num_cycles = 25;
#ifdef __GNUC__
  for (__attribute__ ((unused)) auto const cycle : range(num_cycles)) { 
#else
  for (auto const cycle : range(num_cycles)) { 
#endif

    error = 0;
    auto R_old = R;
    auto lambda_old = lambda;

    for (auto i : range(spin_names.size())) {
      auto block = spin_names[i];
      //matrix<double> const &R_b = R[i];
      //matrix<double> const &lambda_b = lambda[i];
      //matrix<double> &D_b = D[i];
      //matrix<double> &lambda_c_b = lambda_c[i];
      auto g_iw_b = g_iw[i];
      auto g0_iw_b = g0_iw[i];
      auto g0_k_iw_b = g0_k_iw[i];

      auto const &R_b = R.at(block);
      auto const &lambda_b = lambda.at(block);
      auto &D_b = D.at(block);
      auto &lambda_c_b = lambda_c.at(block);

      // Calculate new sigma_iw for this block
      auto sigma_iw_b = get_sigma_z(g_iw_b,R_b,lambda_b,mu);

      // Calculate new g_iw:
      for (auto const &iw : iw_mesh) {
        g_iw_b[iw] = 0.0;
        for (auto const &k : k_mesh) {
          g_iw_b[iw] += inverse( inverse(g0_k_iw_b[k,iw]) + mu - sigma_iw_b[iw] ) / k_mesh.size();
        }
      }

      // Calculate new g0_iw:
      for (auto const &iw : iw_mesh) {
        g0_iw_b[iw] = inverse( inverse(g_iw_b[iw]) + sigma_iw_b[iw] );
      }

      // Calculate hybridization function
      auto delta_iw_b = get_delta_z(g0_iw_b);

      // RISB self-consistent part to calculate new sigma_iw
      auto pdensity = get_pdensity_gf(g_iw_b, R_b);
      auto ke = get_ke_gf(g_iw_b, delta_iw_b, R_b);

      D_b = get_d<double> (pdensity, ke);
      lambda_c_b = get_lambda_c<double>(pdensity, R_b, lambda_b, D_b);
    }

    emb_solver.set_h_emb(h_loc,lambda_c, D);
    emb_solver.solve();

    for (auto i : range(spin_names.size())) {
      auto block = spin_names[i];
      //matrix<double> &R_b = R[i];
      //matrix<double> &lambda_b = lambda[i];
      //matrix<double> const &D_b = D[i];
      //matrix<double> const &lambda_c_b = lambda_c[i];

      auto &R_b = R.at(block);
      auto &lambda_b = lambda.at(block);
      auto const &D_b = D.at(block);
      auto const &lambda_c_b = lambda_c.at(block);

      auto Nf = emb_solver.get_nf(block);
      auto Mcf = emb_solver.get_mcf(block);

      lambda_b =  get_lambda(R_b, D_b, lambda_c_b, Nf);
      R_b = get_r(Mcf, Nf);

      error = frobenius_norm(matrix<double>(R_b - R_old.at(block)));
      error += frobenius_norm(matrix<double>(lambda_b - lambda_old.at(block)));
    }
  
    if (error < 1e-6) {
      total_cycles = cycle;
      break;
    }
  }
  
  std::cout << "cycles = " << total_cycles << "  error = " << error << std::endl;
  std::cout << "R = " << R.at("up") << std::endl;
  std::cout << "lambda = " << lambda.at("up") << std::endl;

  double mu_calculated = 0;
  for (auto block : spin_names) mu_calculated += trace(lambda.at(block)) / 2;
  double mu_expected = U / 2.0;
  matrix<double> R_expected = {{{0.986323}}};
  matrix<double> lambda_expected = {{{mu_expected}}};

  EXPECT_NEAR(mu_expected, mu_calculated, 1e-3); // NOLINT
  for (auto block : spin_names) {
    EXPECT_ARRAY_NEAR(R_expected, R.at(block), 1e-3); // NOLINT
    EXPECT_ARRAY_NEAR(lambda_expected, lambda.at(block), 1e-3); // NOLINE
  }
}


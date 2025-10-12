from librairies import *

def get_BL(tau, sigma, pi, P, Q, omega):

    if isinstance(sigma, pd.DataFrame):
        sigma = sigma.values
    else:
        sigma = np.asarray(sigma)

    if isinstance(P, pd.DataFrame):
        P = P.values
    else:
        P = np.asarray(P)

    if isinstance(pi, pd.Series):
        pi = pi.reindex().to_numpy().reshape(-1, 1)
    else:
        pi = np.asarray(pi)

    if isinstance(Q, pd.Series):
        Q = Q.to_numpy().reshape(-1, 1)
    else:
        Q = np.asarray(Q)

    if isinstance(omega, pd.DataFrame) :
        omega = omega.values 
    else:
        omega = np.asarray(omega)


    mu_bl = inv((1/tau)*inv(sigma) + P.T @ inv(omega) @ P) @ ((1/tau)*inv(sigma) @ pi + P.T @ inv(omega) @ Q)
    sigma_bl = sigma + inv((1/tau)*inv(sigma) + P.T @ inv(omega) @ P)

    return mu_bl, sigma_bl
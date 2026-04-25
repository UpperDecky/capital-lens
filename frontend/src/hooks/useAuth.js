export function useAuth() {
  const getToken = () => localStorage.getItem('cl_token')
  const isAuthenticated = () => Boolean(getToken())
  const logout = () => localStorage.removeItem('cl_token')
  return { getToken, isAuthenticated, logout }
}

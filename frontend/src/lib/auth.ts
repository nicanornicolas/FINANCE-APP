import api from './api';
import Cookies from 'js-cookie';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await api.post('/auth/login', credentials);
    const authData = response.data;

    // Store tokens in cookies
    Cookies.set('access_token', authData.access_token, { expires: 1 });
    Cookies.set('refresh_token', authData.refresh_token, { expires: 7 });

    return authData;
  },

  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await api.post('/auth/register', data);
    const authData = response.data;

    // Store tokens in cookies
    Cookies.set('access_token', authData.access_token, { expires: 1 });
    Cookies.set('refresh_token', authData.refresh_token, { expires: 7 });

    return authData;
  },

  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear tokens
      Cookies.remove('access_token');
      Cookies.remove('refresh_token');
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get('/auth/profile');
    return response.data;
  },

  async forgotPassword(email: string): Promise<void> {
    await api.post('/auth/forgot-password', { email });
  },

  isAuthenticated(): boolean {
    return !!Cookies.get('access_token');
  },

  getToken(): string | undefined {
    return Cookies.get('access_token');
  },
};

export default authService;
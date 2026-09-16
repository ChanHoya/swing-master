import axios from 'axios';

// 백엔드 API의 기본 주소 (로컬 8000)
export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

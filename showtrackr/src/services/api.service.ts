import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

class ApiService {
  private api: AxiosInstance

  constructor(baseURL: string) {
    this.api = axios.create({
      baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    })

    // Add request interceptor for logging, authentication, etc.
    this.api.interceptors.request.use(
      (config) => {
        // You can add auth tokens here if needed
        return config
      },
      (error) => {
        return Promise.reject(error)
      },
    )

    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => {
        return response
      },
      (error) => {
        // Handle errors globally
        if (error.response) {
          // Server responded with a status code outside of 2xx range
          console.error('API Error:', error.response.status, error.response.data)
        } else if (error.request) {
          // Request was made but no response received
          console.error('API Request Error:', error.request)
        } else {
          // Error in setting up the request
          console.error('API Setup Error:', error.message)
        }

        return Promise.reject(error)
      },
    )
  }

  public async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.get(url, config)
    return response.data
  }

  public async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.post(url, data, config)
    return response.data
  }

  public async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.put(url, data, config)
    return response.data
  }

  public async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.delete(url, config)
    return response.data
  }
}

export default ApiService

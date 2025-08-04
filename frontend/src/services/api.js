// API service module for communicating with the RAG backend
import {
  QUERY_ENDPOINT,
  HEALTH_ENDPOINT,
  SIMILARITY_ENDPOINT,
  STATS_ENDPOINT,
  INFO_ENDPOINT,
  INGEST_ENDPOINT,
  ROOT_ENDPOINT,
  getBaseUrl
} from '../config/endpoints';

const BASE_URL = getBaseUrl();

// Helper function for making HTTP requests
const makeRequest = async (url, options = {}) => {
  const fullUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`;
  
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options
  };

  try {
    console.log(`Making request to: ${fullUrl}`, defaultOptions);
    
    const response = await fetch(fullUrl, defaultOptions);
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`Request failed for ${fullUrl}:`, error);
    throw new Error(`Request failed: ${error.message}`);
  }
};

// Send a chat message to the RAG system
export const sendMessage = async (question, returnSources = true) => {
  if (!question || typeof question !== 'string' || question.trim() === '') {
    throw new Error('Question is required and must be a non-empty string');
  }

  try {
    const response = await makeRequest(QUERY_ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({
        question: question.trim(),
        return_sources: returnSources
      })
    });
    
    return response;
  } catch (error) {
    console.error('Error sending message:', error);
    throw new Error(`Failed to send message: ${error.message}`);
  }
};

// Check backend health
export const getHealth = async () => {
  try {
    const response = await makeRequest(HEALTH_ENDPOINT, {
      method: 'GET'
    });
    return response;
  } catch (error) {
    console.error('Error checking health:', error);
    throw new Error(`Health check failed: ${error.message}`);
  }
};

// Get similar documents for a query
export const getSimilarDocuments = async (query, k = 4) => {
  if (!query || typeof query !== 'string' || query.trim() === '') {
    throw new Error('Query is required and must be a non-empty string');
  }

  if (k < 1 || k > 20) {
    throw new Error('k must be between 1 and 20');
  }

  try {
    const response = await makeRequest(SIMILARITY_ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({
        query: query.trim(),
        top_k: k
      })
    });
    
    return {
      query: response.query,
      documents: response.results
    };
  } catch (error) {
    console.error('Error getting similar documents:', error);
    throw new Error(`Failed to get similar documents: ${error.message}`);
  }
};

// Get collection statistics
export const getStats = async () => {
  try {
    const response = await makeRequest(STATS_ENDPOINT, {
      method: 'GET'
    });
    return response;
  } catch (error) {
    console.error('Error getting stats:', error);
    throw new Error(`Failed to get stats: ${error.message}`);
  }
};

// Get system information
export const getInfo = async () => {
  try {
    const response = await makeRequest(INFO_ENDPOINT, {
      method: 'GET'
    });
    return response;
  } catch (error) {
    console.error('Error getting info:', error);
    throw new Error(`Failed to get info: ${error.message}`);
  }
};

// Ingest new documents (optional endpoint)
export const ingestDocuments = async () => {
  try {
    const response = await makeRequest(INGEST_ENDPOINT, {
      method: 'POST'
    });
    return response;
  } catch (error) {
    console.error('Error ingesting documents:', error);
    throw new Error(`Failed to ingest documents: ${error.message}`);
  }
};

// Utility function to test API connectivity
export const testConnection = async () => {
  try {
    const response = await makeRequest(ROOT_ENDPOINT, {
      method: 'GET'
    });
    return response;
  } catch (error) {
    console.error('Error testing connection:', error);
    throw new Error(`Connection test failed: ${error.message}`);
  }
};

// Export all functions as default object for convenience
const api = {
  sendMessage,
  getHealth,
  getSimilarDocuments,
  getStats,
  getInfo,
  ingestDocuments,
  testConnection,
};

export default api;
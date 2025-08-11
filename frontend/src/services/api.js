// API service module for communicating with the RAG backend
import {
  QUERY_ENDPOINT,
  STREAM_QUERY_ENDPOINT,
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

  // Добавляем таймаут 10 минут (600 секунд)
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 минут

  try {
    console.log(`Making request to: ${fullUrl}`, defaultOptions);
    
    const response = await fetch(fullUrl, {
      ...defaultOptions,
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    clearTimeout(timeoutId);
    console.error(`Request failed for ${fullUrl}:`, error);
    
    if (error.name === 'AbortError') {
      throw new Error('Request timeout: Превышено время ожидания ответа (10 минут)');
    }
    
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

// Stream a chat message from the RAG system (Server-Sent Events or chunked text)
export const streamMessage = async (question, onToken, options = {}) => {
  if (!question || typeof question !== 'string' || question.trim() === '') {
    throw new Error('Question is required and must be a non-empty string');
  }

  // Если STREAM_QUERY_ENDPOINT относительный — добавим BASE_URL
  const baseStreamUrl = STREAM_QUERY_ENDPOINT.startsWith('http')
    ? STREAM_QUERY_ENDPOINT
    : `${BASE_URL}${STREAM_QUERY_ENDPOINT}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 min

  // Пытаемся использовать EventSource (GET) для dev-прокси CRA, затем POST, затем GET через fetch
  const tryEventSource = async () => {
    if (typeof window === 'undefined' || typeof window.EventSource === 'undefined') {
      throw new Error('EventSource is not available');
    }
    const url = `${baseStreamUrl}?question=${encodeURIComponent(question.trim())}`;
    console.log('[streamMessage] EventSource opening:', url);
    return await new Promise((resolve, reject) => {
      const es = new EventSource(url, { withCredentials: false });
      let opened = false;
      let done = false;

      const cleanup = () => {
        try { es.close(); } catch (_) {}
        clearTimeout(timeoutId);
      };

      es.onopen = () => {
        opened = true;
        console.log('[streamMessage] EventSource open');
      };

      es.onmessage = (e) => {
        const payload = (e && e.data) || '';
        if (payload === '[DONE]') {
          done = true;
          cleanup();
          resolve();
          return;
        }
        try {
          let text;
          if (payload && payload.startsWith('{')) {
            const obj = JSON.parse(payload);
            text = obj.token || obj.text || '';
          } else {
            text = payload;
          }
          if (text) {
            // Немедленно вызываем колбэк для реального времени
            onToken(text);
          }
        } catch (err) {
          onToken(payload);
        }
      };

      es.onerror = (err) => {
        // Если соединение не открылось — считаем ошибкой/фолбэком
        console.warn('[streamMessage] EventSource error', err);
        cleanup();
        if (!opened || !done) {
          reject(new Error('EventSource failed'));
        } else {
          resolve();
        }
      };
    });
  };

  // Пытаемся сначала POST (чтобы передавать длинные вопросы), затем фолбэк на GET (EventSource-совместимость)
  const tryPost = async () => {
    const response = await fetch(baseStreamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      body: JSON.stringify({ question: question.trim() }),
      signal: controller.signal,
    });
    return response;
  };

  const tryGet = async () => {
    const url = `${baseStreamUrl}?question=${encodeURIComponent(question.trim())}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        ...(options.headers || {}),
      },
      signal: controller.signal,
    });
    return response;
  };

  const readStream = async (response) => {
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const data = await response.json();
      const text = data?.answer || '';
      if (text) onToken(text);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Streaming not supported by the browser or response has no body');
    }

    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let doneAll = false;

    while (!doneAll) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx;
      while ((idx = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 1);

        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith('data:')) {
          const payload = trimmed.slice(5).trim();
          if (payload === '[DONE]') {
            doneAll = true;
            break;
          }
          try {
            let text;
            if (payload.startsWith('{')) {
              const obj = JSON.parse(payload);
              text = obj.token || obj.text || '';
            } else {
              text = payload;
            }
            if (text) {
              // Немедленно вызываем колбэк для реального времени
              onToken(text);
            }
          } catch {
            onToken(payload);
          }
        } else {
          onToken(trimmed);
        }
      }
    }
  };

  try {
    // 1) Сначала пробуем EventSource (лучше всего работает сквозь dev-прокси CRA)
    try {
      await tryEventSource();
      return;
    } catch (esErr) {
      console.log('[streamMessage] EventSource fallback to fetch. Reason:', esErr?.message || esErr);
    }

    // 2) Пробуем POST fetch-стрим
    try {
      const resp = await tryPost();
      await readStream(resp);
      return;
    } catch (postErr) {
      console.log('[streamMessage] POST fetch fallback to GET. Reason:', postErr?.message || postErr);
    }

    // 3) Фолбэк на GET fetch-стрим
    const resp = await tryGet();
    await readStream(resp);
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Request timeout: Превышено время ожидания ответа (10 минут)');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
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
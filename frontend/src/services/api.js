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

// Моковые данные для демонстрации
const MOCK_DATA = {
  health: {
    status: 'ok',
    timestamp: new Date().toISOString(),
    components: {
      database: 'ok',
      vector_store: 'ok',
      llm_service: 'ok',
      api_gateway: 'ok'
    },
    recommendations: []
  },
  
  info: {
    version: '1.0.0',
    name: 'RAG Chat System',
    description: 'Система чата с использованием RAG (Retrieval-Augmented Generation)',
    features: [
      'Чат с ИИ',
      'Поиск по документам',
      'Анализ контекста',
      'История сообщений'
    ],
    environment: 'development'
  },
  
  stats: {
    total_documents: 150,
    total_chunks: 1250,
    collection_size_mb: 45.2,
    last_updated: new Date().toISOString(),
    embeddings_model: 'text-embedding-3-small',
    llm_model: 'mistral-large-latest'
  },
  
  responses: [
    {
      question: 'Что такое RAG?',
      answer: 'RAG (Retrieval-Augmented Generation) - это техника, которая объединяет поиск информации с генерацией текста. Система сначала находит релевантные документы, а затем использует их для создания более точных и информативных ответов.',
      sources: [
        {
          title: 'Введение в RAG',
          content: 'RAG позволяет ИИ-моделям получать доступ к актуальной информации...',
          score: 0.95
        }
      ]
    },
    {
      question: 'Как работает система?',
      answer: 'Наша система работает следующим образом: 1) Получает ваш вопрос, 2) Ищет релевантные документы в базе знаний, 3) Использует найденную информацию для генерации ответа, 4) Предоставляет источники для проверки.',
      sources: [
        {
          title: 'Архитектура системы',
          content: 'Система состоит из компонентов: векторная база данных, LLM модель, API шлюз...',
          score: 0.92
        },
        {
          title: 'Процесс обработки',
          content: 'Вопрос обрабатывается через несколько этапов: токенизация, поиск, генерация...',
          score: 0.88
        }
      ]
    },
    {
      question: 'Какие документы доступны?',
      answer: 'В системе доступны различные типы документов: техническая документация, руководства пользователей, научные статьи, новостные материалы и другие источники информации. Все документы индексируются и доступны для поиска.',
      sources: [
        {
          title: 'База знаний',
          content: 'База содержит 150 документов различных типов и тематик...',
          score: 0.89
        }
      ]
    }
  ]
};

// Функция для получения мокового ответа на основе вопроса
const getMockResponse = (question) => {
  const lowerQuestion = question.toLowerCase();
  
  // Ищем подходящий ответ в моковых данных
  for (const response of MOCK_DATA.responses) {
    if (lowerQuestion.includes('rag') || lowerQuestion.includes('что такое')) {
      return MOCK_DATA.responses[0];
    }
    if (lowerQuestion.includes('как работает') || lowerQuestion.includes('система')) {
      return MOCK_DATA.responses[1];
    }
    if (lowerQuestion.includes('документ') || lowerQuestion.includes('доступн')) {
      return MOCK_DATA.responses[2];
    }
  }
  
  // Если не найдено точного совпадения, возвращаем общий ответ
  return {
    question: question,
    answer: `Спасибо за ваш вопрос: "${question}". Это демонстрационная версия системы RAG. В реальной системе здесь был бы ответ, основанный на поиске в базе знаний. Система может отвечать на вопросы о различных темах, используя индексированные документы.`,
    sources: [
      {
        title: 'Демонстрационный ответ',
        content: 'Это моковый ответ для демонстрации работы интерфейса.',
        score: 0.85
      }
    ]
  };
};

// Helper function for making HTTP requests (теперь возвращает моковые данные)
const makeRequest = async (url, options = {}) => {
  // Имитируем задержку сети
  await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 1000));
  
  console.log(`Mock request to: ${url}`, options);
  
  // Возвращаем соответствующие моковые данные в зависимости от эндпоинта
  switch (url) {
    case HEALTH_ENDPOINT:
      return MOCK_DATA.health;
    case INFO_ENDPOINT:
      return MOCK_DATA.info;
    case STATS_ENDPOINT:
      return MOCK_DATA.stats;
    case ROOT_ENDPOINT:
      return { message: 'RAG API is running', version: '1.0.0' };
    default:
      throw new Error(`Mock endpoint ${url} not implemented`);
  }
};

// Send a chat message to the RAG system
export const sendMessage = async (question, returnSources = true) => {
  if (!question || typeof question !== 'string' || question.trim() === '') {
    throw new Error('Question is required and must be a non-empty string');
  }

  // Имитируем задержку обработки
  await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));
  
  console.log(`Mock sending message: ${question}`);
  
  const response = getMockResponse(question);
  
  // Если не нужны источники, убираем их
  if (!returnSources) {
    delete response.sources;
  }
  
  return response;
};

// Check backend health
export const getHealth = async () => {
  try {
    const response = await makeRequest(HEALTH_ENDPOINT);
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

  // Имитируем задержку
  await new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 500));
  
  console.log(`Mock getting similar documents for: ${query}`);
  
  return {
    query: query.trim(),
    documents: [
      {
        title: 'Документ 1',
        content: 'Содержание первого документа, релевантного запросу...',
        score: 0.95,
        metadata: { source: 'doc1.pdf', page: 1 }
      },
      {
        title: 'Документ 2', 
        content: 'Содержание второго документа с полезной информацией...',
        score: 0.87,
        metadata: { source: 'doc2.pdf', page: 3 }
      },
      {
        title: 'Документ 3',
        content: 'Дополнительная информация по теме запроса...',
        score: 0.82,
        metadata: { source: 'doc3.pdf', page: 5 }
      }
    ].slice(0, k)
  };
};

// Get collection statistics
export const getStats = async () => {
  try {
    const response = await makeRequest(STATS_ENDPOINT);
    return response;
  } catch (error) {
    console.error('Error getting stats:', error);
    throw new Error(`Failed to get stats: ${error.message}`);
  }
};

// Get system information
export const getInfo = async () => {
  try {
    const response = await makeRequest(INFO_ENDPOINT);
    return response;
  } catch (error) {
    console.error('Error getting info:', error);
    throw new Error(`Failed to get info: ${error.message}`);
  }
};

// Ingest new documents (optional endpoint)
export const ingestDocuments = async (filePath, chunkSize = 1000, chunkOverlap = 200) => {
  if (!filePath || typeof filePath !== 'string' || filePath.trim() === '') {
    throw new Error('File path is required and must be a non-empty string');
  }

  // Имитируем задержку индексации
  await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 3000));
  
  console.log(`Mock ingesting document: ${filePath}`);
  
  return {
    message: 'Document ingested successfully',
    file_path: filePath.trim(),
    chunks_created: Math.floor(Math.random() * 50) + 10,
    processing_time: Math.floor(Math.random() * 10) + 2
  };
};

// Utility function to test API connectivity
export const testConnection = async () => {
  try {
    const response = await makeRequest(ROOT_ENDPOINT);
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
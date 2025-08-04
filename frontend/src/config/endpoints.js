// Конфигурация API эндпоинтов
export const QUERY_ENDPOINT = '/api/query';
export const HEALTH_ENDPOINT = '/health';
export const SIMILARITY_ENDPOINT = '/api/similarity';
export const STATS_ENDPOINT = '/api/stats';
export const INFO_ENDPOINT = '/api/info';
export const INGEST_ENDPOINT = '/api/ingest';
export const ROOT_ENDPOINT = '/';

// Функция для определения базового URL в зависимости от окружения
export const getBaseUrl = () => {
  // В development режиме используем прокси (относительные пути)
  if (process.env.NODE_ENV === 'development') {
    return '';
  }
  
  // В production используем переменную окружения или IP адрес бэкенда
  return process.env.REACT_APP_API_BASE_URL || 'http://10.77.160.35:8000';
}; 
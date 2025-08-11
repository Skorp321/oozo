// Конфигурация API эндпоинтов
export const QUERY_ENDPOINT = '/api/query';
export const STREAM_QUERY_ENDPOINT = '/api/query/stream';
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
  
  // В production используем переменную окружения (поддерживаем оба имени), иначе сервисное имя Docker
  return (
    process.env.REACT_APP_API_BASE_URL ||
    process.env.REACT_APP_API_URL ||
    'http://rag-app:8000'
  );
}; 
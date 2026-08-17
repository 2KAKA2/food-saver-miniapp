export const LEGAL_VERSION = import.meta.env.VITE_LEGAL_VERSION || '2026-08-17'
export const OPERATOR_NAME = import.meta.env.VITE_OPERATOR_NAME || '食尽其用运营者'
export const AI_PROVIDER_NAME = import.meta.env.VITE_AI_PROVIDER_NAME || '北京智谱华章科技有限公司（智谱AI）'

export const LEGAL_DATE_LABEL = LEGAL_VERSION.replace(
  /^(\d{4})-(\d{2})-(\d{2})$/,
  '$1年$2月$3日',
)

export type ContactDisplayType = 'NO' | 'NC'

export function contactTypeDescription(contactType: ContactDisplayType) {
  return contactType === 'NO' ? '평상시 열림(NO)' : '평상시 닫힘(NC)'
}

export function ContactTypeBadge({ contactType }: { contactType: ContactDisplayType }) {
  const description = contactTypeDescription(contactType)
  return <span className={`contact-type-badge ${contactType.toLowerCase()}`} title={description} aria-label={description}>{contactType}</span>
}

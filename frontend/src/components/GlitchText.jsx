export default function GlitchText({ children, className = '', as: Tag = 'span' }) {
  return (
    <Tag className={`glitch ${className}`} data-text={children}>
      {children}
    </Tag>
  )
}

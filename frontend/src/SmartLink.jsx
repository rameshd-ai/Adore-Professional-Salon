import { Link } from 'react-router-dom'

export default function SmartLink({ to, href, className, children, ...rest }) {
  const target = to ?? href ?? '#'
  // In-app routes: /path or /path#hash (not http(s)://)
  if (
    typeof target === 'string' &&
    target.startsWith('/') &&
    !target.startsWith('//')
  ) {
    return (
      <Link className={className} to={target} {...rest}>
        {children}
      </Link>
    )
  }
  return (
    <a className={className} href={target} {...rest}>
      {children}
    </a>
  )
}

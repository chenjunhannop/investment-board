import type { ReactNode } from 'react';

interface Props {
  title: string;
  children: ReactNode;
  className?: string;
}

export default function BigScreenPanel({ title, children, className = '' }: Props) {
  return (
    <section className={`bs-panel ${className}`}>
      <span className="bs-corner tl" />
      <span className="bs-corner tr" />
      <span className="bs-corner bl" />
      <span className="bs-corner br" />
      <h3 className="bs-panel-title">{title}</h3>
      <div className="bs-panel-body">{children}</div>
    </section>
  );
}

"use client";

import { useEffect, useState } from "react";
import DOMPurify from "dompurify";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

type Props = {
  content: string;
  className?: string;
};

function looksLikeHtml(text: string): boolean {
  return /^\s*</.test(text);
}

export function StatementContent({ content, className = "" }: Props) {
  const [safeHtml, setSafeHtml] = useState<string | null>(null);

  useEffect(() => {
    if (!looksLikeHtml(content)) {
      setSafeHtml(null);
      return;
    }
    setSafeHtml(DOMPurify.sanitize(content));
  }, [content]);

  if (!content.trim()) {
    return <p className={`text-slate-500 ${className}`}>No statement.</p>;
  }

  if (looksLikeHtml(content)) {
    if (safeHtml === null) {
      return <div className={`prose prose-invert max-w-none text-sm ${className}`} />;
    }
    return (
      <div
        className={`prose prose-invert max-w-none text-sm ${className}`}
        dangerouslySetInnerHTML={{ __html: safeHtml }}
      />
    );
  }

  return (
    <div className={`prose prose-invert max-w-none text-sm ${className}`}>
      <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{content}</ReactMarkdown>
    </div>
  );
}

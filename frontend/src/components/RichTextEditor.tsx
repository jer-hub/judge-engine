"use client";

import { useEffect, useId, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { marked } from "marked";

import "react-quill/dist/quill.snow.css";

const ReactQuill = dynamic(() => import("react-quill"), {
  ssr: false,
  loading: () => (
    <div className="flex min-h-[220px] items-center justify-center rounded-b-lg bg-slate-900 text-sm text-slate-500">
      Loading editor…
    </div>
  ),
});

type Props = {
  id?: string;
  name?: string;
  label?: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  minHeight?: number;
};

function looksLikeHtml(text: string): boolean {
  return /^\s*</.test(text);
}

function toEditorHtml(value: string): string {
  if (!value.trim()) return "";
  if (looksLikeHtml(value)) return value;
  return marked.parse(value, { async: false }) as string;
}

function isEmptyHtml(html: string): boolean {
  const text = html
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/g, " ")
    .trim();
  return text.length === 0;
}

const TOOLBAR = [
  [{ header: [2, 3, false] }],
  ["bold", "italic", "underline", "strike"],
  [{ list: "ordered" }, { list: "bullet" }],
  ["blockquote", "code-block"],
  ["link"],
  ["clean"],
];

let linkSanitizerInstalled = false;

function installLinkSanitizer() {
  if (linkSanitizerInstalled || typeof window === "undefined") return;
  linkSanitizerInstalled = true;
  void import("quill").then((mod) => {
    const Quill = mod.default;
    const Link = Quill.import("formats/link") as {
      sanitize: (url: string) => string;
    };
    const previous = Link.sanitize.bind(Link);
    Link.sanitize = (url: string) => {
      const cleaned = previous(url);
      if (!/^(https?:\/\/|mailto:|ftp:\/\/)/i.test(cleaned)) {
        return "about:blank";
      }
      return cleaned;
    };
  });
}

export function RichTextEditor({
  id,
  name = "statement",
  label = "Statement",
  value,
  onChange,
  required,
  minHeight = 220,
}: Props) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const [html, setHtml] = useState(() => toEditorHtml(value));

  useEffect(() => {
    installLinkSanitizer();
  }, []);

  useEffect(() => {
    const next = toEditorHtml(value);
    setHtml((prev) => (prev === next ? prev : next));
  }, [value]);

  const modules = useMemo(
    () => ({
      toolbar: TOOLBAR,
      clipboard: { matchVisual: false },
    }),
    [],
  );

  function handleChange(next: string) {
    setHtml(next);
    onChange(isEmptyHtml(next) ? "" : next);
  }

  return (
    <div className="sm:col-span-2">
      <label htmlFor={fieldId} className="mb-1 block text-sm text-slate-400">
        {label}
        {required && <span className="sr-only"> (required)</span>}
      </label>

      <div
        className="rich-text-editor overflow-hidden rounded-lg border border-slate-700 bg-slate-900"
        style={{ ["--rte-min-height" as string]: `${minHeight}px` }}
      >
        <ReactQuill
          theme="snow"
          value={html}
          onChange={handleChange}
          modules={modules}
          placeholder="Write the problem statement…"
        />
      </div>

      <textarea
        id={fieldId}
        name={name}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="sr-only"
        tabIndex={-1}
      />
    </div>
  );
}

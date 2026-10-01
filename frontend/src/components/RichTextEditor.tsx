"use client";

import { useEffect, useId, useRef } from "react";
import { EditorContent, useEditor, useEditorState, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Placeholder } from "@tiptap/extensions";
import { marked } from "marked";

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

/** Markdown statements (older problems, seeds) open as their HTML equivalent. */
function toEditorHtml(value: string): string {
  if (!value.trim()) return "";
  if (looksLikeHtml(value)) return value;
  return marked.parse(value, { async: false }) as string;
}

const SAFE_LINK = /^(https?:\/\/|mailto:)/i;

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
  // useEditor keeps its first config; read the latest onChange through a ref
  // so a parent's inline handler never sees stale form state.
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const editor = useEditor({
    // Next.js renders on the server first; build the editor on the client only.
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3] },
        link: {
          openOnClick: false,
          autolink: true,
          defaultProtocol: "https",
          // Same rule the old Quill link sanitizer enforced (no javascript: etc).
          isAllowedUri: (url) => SAFE_LINK.test(url),
          HTMLAttributes: { rel: "noopener noreferrer nofollow", target: "_blank" },
        },
      }),
      Placeholder.configure({ placeholder: "Write the problem statement…" }),
    ],
    content: toEditorHtml(value),
    editorProps: {
      attributes: {
        "aria-label": label,
        class: "rte-content",
      },
    },
    onUpdate: ({ editor }) => {
      onChangeRef.current(editor.isEmpty ? "" : editor.getHTML());
    },
  });

  // Follow external value changes (e.g. switching which problem is edited)
  // without fighting the user's own typing.
  useEffect(() => {
    if (!editor) return;
    const next = toEditorHtml(value);
    const current = editor.isEmpty ? "" : editor.getHTML();
    if (next !== current) {
      editor.commands.setContent(next, { emitUpdate: false });
    }
  }, [editor, value]);

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
        {editor ? (
          <>
            <Toolbar editor={editor} />
            <EditorContent editor={editor} />
          </>
        ) : (
          <div
            className="flex items-center justify-center bg-slate-900 text-sm text-slate-500"
            style={{ minHeight }}
          >
            Loading editor…
          </div>
        )}
      </div>

      {/* Keeps native form semantics (required, name) for the hidden value. */}
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

function Toolbar({ editor }: { editor: Editor }) {
  // Tiptap 3 doesn't re-render on every keystroke; subscribe to what the
  // buttons need to show as active.
  const active = useEditorState({
    editor,
    selector: ({ editor: e }) => ({
      h2: e.isActive("heading", { level: 2 }),
      h3: e.isActive("heading", { level: 3 }),
      bold: e.isActive("bold"),
      italic: e.isActive("italic"),
      underline: e.isActive("underline"),
      strike: e.isActive("strike"),
      bulletList: e.isActive("bulletList"),
      orderedList: e.isActive("orderedList"),
      blockquote: e.isActive("blockquote"),
      codeBlock: e.isActive("codeBlock"),
      link: e.isActive("link"),
    }),
  });

  function editLink() {
    const previous = (editor.getAttributes("link").href as string | undefined) ?? "";
    const url = window.prompt("Link URL (https:// or mailto:)", previous);
    if (url === null) return;
    const trimmed = url.trim();
    if (!trimmed) {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }
    if (!SAFE_LINK.test(trimmed)) {
      window.alert("Only https://, http:// and mailto: links are allowed.");
      return;
    }
    editor.chain().focus().extendMarkRange("link").setLink({ href: trimmed }).run();
  }

  const c = () => editor.chain().focus();
  const groups: Array<Array<{ label: string; title: string; on: boolean; run: () => void }>> = [
    [
      { label: "H2", title: "Heading", on: active.h2, run: () => c().toggleHeading({ level: 2 }).run() },
      { label: "H3", title: "Subheading", on: active.h3, run: () => c().toggleHeading({ level: 3 }).run() },
    ],
    [
      { label: "B", title: "Bold", on: active.bold, run: () => c().toggleBold().run() },
      { label: "I", title: "Italic", on: active.italic, run: () => c().toggleItalic().run() },
      { label: "U", title: "Underline", on: active.underline, run: () => c().toggleUnderline().run() },
      { label: "S", title: "Strikethrough", on: active.strike, run: () => c().toggleStrike().run() },
    ],
    [
      { label: "• List", title: "Bulleted list", on: active.bulletList, run: () => c().toggleBulletList().run() },
      { label: "1. List", title: "Numbered list", on: active.orderedList, run: () => c().toggleOrderedList().run() },
    ],
    [
      { label: "❝", title: "Quote", on: active.blockquote, run: () => c().toggleBlockquote().run() },
      { label: "</>", title: "Code block", on: active.codeBlock, run: () => c().toggleCodeBlock().run() },
      { label: "Link", title: "Add or edit link", on: active.link, run: editLink },
    ],
    [
      {
        label: "Clear",
        title: "Clear formatting",
        on: false,
        run: () => c().unsetAllMarks().clearNodes().run(),
      },
    ],
  ];

  return (
    <div
      role="toolbar"
      aria-label="Formatting"
      className="flex flex-wrap gap-1 border-b border-slate-800 bg-slate-950/80 px-2 py-1.5"
    >
      {groups.map((group, gi) => (
        <div key={gi} className="flex gap-0.5 border-r border-slate-800 pr-1 last:border-r-0">
          {group.map((b) => (
            <button
              key={b.title}
              type="button"
              title={b.title}
              aria-label={b.title}
              aria-pressed={b.on}
              onMouseDown={(e) => e.preventDefault()} // keep the editor's selection
              onClick={b.run}
              className={`cursor-pointer rounded px-2 py-1 text-xs transition ${
                b.on
                  ? "bg-emerald-500/20 text-emerald-300"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              {b.label}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}

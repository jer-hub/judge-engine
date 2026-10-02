"use client";

import Editor, { loader } from "@monaco-editor/react";

// Load Monaco from this app (public/monaco, copied at dev/build time), not
// a CDN: labs without internet access would otherwise get no editor.
loader.config({ paths: { vs: "/monaco/vs" } });

const JAVA_STUB = `import java.util.*;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);

    }
}
`;

type Props = {
  value: string;
  onChange: (value: string) => void;
};

export function CodeEditor({ value, onChange }: Props) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-800">
      <Editor
        height="420px"
        defaultLanguage="java"
        theme="vs-dark"
        value={value}
        onChange={(v) => onChange(v ?? "")}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          scrollBeyondLastLine: false,
          automaticLayout: true,
        }}
      />
    </div>
  );
}

export { JAVA_STUB };

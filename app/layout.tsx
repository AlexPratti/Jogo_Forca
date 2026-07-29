import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Arena da Forca",
  description: "Jogo da Forca integrado com Supabase",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}

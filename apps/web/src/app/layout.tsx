import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata = { title: "Website Intelligence Platform (Internal)", description: "Internal-only website intelligence. All results rendered in-platform." };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="flex">
          <Sidebar />
          <main className="flex-1 p-6 max-w-6xl">{children}</main>
        </div>
      </body>
    </html>
  );
}

import type { Metadata } from 'next';
export const metadata: Metadata={title:'Solar Atlas',description:'Ontario solar study areas and source-based assessment'};
export default function Layout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en"><body style={{margin:0}}>{children}</body></html>;}

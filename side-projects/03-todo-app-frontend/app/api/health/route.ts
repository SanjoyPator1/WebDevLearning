// For App Router (app/api/health/route.ts)
export async function GET() {
  return Response.json({ status: "ok" }, { status: 200 });
}

// OR for Pages Router (pages/api/health.ts)
// import type { NextApiRequest, NextApiResponse } from 'next';
//
// export default function handler(req: NextApiRequest, res: NextApiResponse) {
//   res.status(200).json({ status: 'ok' });
// }

import { NextResponse } from "next/server";

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const id = params.id;
  const {searchParams} = request.nextUrl;
  const sort = searchParams.get("sort");
  console.log("searchParams  ",searchParams)
  console.log("sort  ",typeof sort)
  return NextResponse.json({ message: "hello route msg", id, sort });
}

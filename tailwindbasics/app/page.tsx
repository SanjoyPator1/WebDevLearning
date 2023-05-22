import Image from "next/image";
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"] });

export default function Home() {
  return (
    <div className="grid grid-cols-3 gap-4 p-2">
      <div className="col-start-2 bg-red-500 rounded-md">01</div>
      <div className="bg-red-500 rounded-md">02</div>
      <div className="bg-red-500 rounded-md">03</div>
      <div className="col-span-2 bg-blue-500 rounded-md">04</div>
      <div className="bg-red-500 rounded-md">05</div>
      <div className="col-start-2 col-end-4 bg-red-500 rounded-md">06</div>
    </div>
  );
}

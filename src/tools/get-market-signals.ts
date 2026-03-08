import { getMarketSignals } from "../lib/notion.js";

export interface GetMarketSignalsInput {
  title: string;
  author?: string;
}

export async function executeGetMarketSignals(
  args: GetMarketSignalsInput
): Promise<{
  title: string;
  author?: string;
  average_hammer_price: number;
  sales_count: number;
  sales: Array<{ hammer_price: number; sale_date?: string; citation?: string }>;
}> {
  const result = await getMarketSignals(args.title, args.author);
  return result;
}

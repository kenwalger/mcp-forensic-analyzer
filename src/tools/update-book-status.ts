import { updateBookStatus } from "../lib/notion.js";

export interface UpdateBookStatusInput {
  page_id: string;
  status: string;
}

export async function executeUpdateBookStatus(
  args: UpdateBookStatusInput
): Promise<{ success: boolean; page_id: string }> {
  return updateBookStatus(args.page_id, args.status);
}

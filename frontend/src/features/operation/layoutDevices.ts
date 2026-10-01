// Symbol centres in the shipped 992×1402 PDF page-5 renders, visually checked
// for all 18 problems. CAP blanks are deliberately not devices. No wiring data.
export type LayoutDevice = { id: string; x: number; y: number }
type Group = [number, number, string, string?]
const groups: Record<string, Group[]> = {
  '001': [[205,677,'PB1','PB0'],[339,677,'SS'],[764,677,'RL','GL'],[294,800,'YL','BZ']],
  '002': [[294,677,'YL','BZ'],[719,677,'GL','RL'],[854,677,'SS'],[272,800,'PB0','PB1']],
  '003': [[294,677,'PB0','PB1'],[719,677,'YL','BZ'],[854,677,'RL','GL'],[272,800,'SS']],
  '004': [[294,677,'YL','BZ'],[719,677,'RL','GL'],[854,677,'SS'],[764,800,'PB0','PB1']],
  '005': [[294,677,'RL','GL'],[719,677,'SS'],[854,677,'PB0','PB1'],[764,800,'YL','BZ']],
  '006': [[294,677,'YL','BZ'],[719,677,'RL','GL'],[854,677,'SS'],[272,800,'PB1','PB0']],
  '007': [[294,677,'YL','BZ'],[719,677,'RL','GL'],[854,677,'SS'],[272,800,'PB0','PB1']],
  '008': [[205,677,'PB0','PB1'],[339,677,'SS'],[764,677,'GL','RL'],[786,800,'YL','BZ']],
  '009': [[205,677,'SS'],[339,677,'RL','GL'],[764,677,'YL','BZ'],[786,800,'PB0','PB1']],
  '010': [[294,677,'PB0','PB1'],[719,677,'WL','YL'],[854,677,'GL','RL'],[272,800,'PB2']],
  '011': [[205,677,'PB2'],[339,677,'GL','RL'],[764,677,'WL','YL'],[294,800,'PB0','PB1']],
  '012': [[294,677,'GL','RL'],[719,677,'PB2'],[854,677,'PB0','PB1'],[764,800,'WL','YL']],
  '013': [[294,677,'WL','YL'],[719,677,'GL','RL'],[854,677,'PB2'],[272,800,'PB0','PB1']],
  '014': [[294,677,'PB2'],[719,677,'PB0','PB1'],[854,677,'WL','YL'],[272,800,'GL','RL']],
  '015': [[205,677,'RL','GL'],[339,677,'WL','YL'],[764,677,'PB1','PB0'],[294,800,'PB2']],
  '016': [[205,677,'RL','GL'],[339,677,'WL','YL'],[764,677,'PB0','PB1'],[786,800,'PB2']],
  '017': [[294,677,'PB0','PB1'],[719,677,'WL','YL'],[854,677,'RL','GL'],[764,800,'PB2']],
  '018': [[205,677,'PB2'],[339,677,'RL','GL'],[764,677,'WL','YL'],[786,800,'PB0','PB1']],
}
export function layoutDevices(problemId: string): LayoutDevice[] {
  if (!/^qnet_electrician_practical_\d{3}$/.test(problemId)) return []
  return (groups[problemId.slice(-3)] ?? []).flatMap(([x,y,first,second]) =>
    [{ id: first, x, y }, ...(second ? [{ id: second, x, y: y+27 }] : [])])
}

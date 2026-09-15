/** 원 단위 int → 사람이 읽는 금액 표기. 1억원 이상은 억 단위(소수 1자리), 미만은 만원 단위(만원 미만 절사). */

const MANWON = 10_000;
const EOK = 100_000_000;

export function formatKrw(won: number): string {
  if (won === 0) return "0원";

  if (Math.abs(won) >= EOK) {
    const eok = Math.round((won / EOK) * 10) / 10;
    return `${eok.toFixed(1)}억원`;
  }

  const manwon = Math.trunc(won / MANWON);
  return `${manwon.toLocaleString("ko-KR")}만원`;
}

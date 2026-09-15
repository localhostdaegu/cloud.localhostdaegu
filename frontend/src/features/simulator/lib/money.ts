/** 폼 숫자 입력 UX용 원↔만원 변환. 내부 상태(FinanceInput)는 항상 원 단위 int로 유지한다. */

const WON_PER_MANWON = 10_000;

export function wonToManwon(won: number): number {
  return Math.round(won / WON_PER_MANWON);
}

export function manwonToWon(manwon: number): number {
  return manwon * WON_PER_MANWON;
}

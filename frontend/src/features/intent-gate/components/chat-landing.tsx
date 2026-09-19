"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { INDUSTRY_LABELS } from "@/shared/daegu";
import { parseIntent, type ParseIntentResult } from "../api";
import { intentToUrl } from "../lib/intent-url";
import { HeroVisual } from "./hero-visual";
import styles from "./chat-landing.module.css";

// 예시는 실제로 끝까지 이어지는 질문만 둔다 — 예산만으로 업종을 골라 주는 역매칭은 아직 없다.
const EXAMPLE_CHIPS = ["서문시장 근처 카페, 예산 5천", "동성로에 미용실", "수성구에서 헬스장, 예산 8천"];

export function ChatLanding() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState("");
  // industry가 missing인데 district는 확정된 응답 — 업종 칩으로 되물어 재제출 없이 바로 라우팅한다.
  const [awaitingIndustry, setAwaitingIndustry] = useState<ParseIntentResult | null>(null);

  const mutation = useMutation({
    mutationFn: parseIntent,
    onSuccess: (result) => {
      if (result.missing.includes("industry") && result.district_code) {
        setAwaitingIndustry(result);
        return;
      }
      router.push(intentToUrl(result));
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || mutation.isPending) return;
    setAwaitingIndustry(null);
    mutation.mutate(trimmed);
  }

  function handlePickIndustry(id: string) {
    if (!awaitingIndustry) return;
    router.push(intentToUrl({ ...awaitingIndustry, industry_id: id }));
  }

  // B유형(업종 랭킹) 직행 경로 — industry_id를 채우지 않고 그대로 라우팅한다.
  // intentToUrl은 industry_id가 null이면 industry 파라미터를 생략하므로 /map?district=...만 남는다.
  function handleSkipIndustry() {
    if (!awaitingIndustry) return;
    router.push(intentToUrl(awaitingIndustry));
  }

  return (
    <main className={styles.landing}>
      <section className={styles.hero} aria-labelledby="home-title">
        <div className={styles.heroCopy}>
          <p className={styles.eyebrow}><span aria-hidden="true" />대구 창업 금융 네비게이터</p>
          <h1 id="home-title">대구에서 여는 내 가게,<br /><span>상권부터 자금까지.</span></h1>
          <p className={styles.intro}>어느 동네에서, 얼마로 시작할까요?<br />막연했던 창업 계획을 데이터로 구체화해 보세요.</p>

          <form id="start" onSubmit={handleSubmit} className={styles.searchForm}>
            <label htmlFor="startup-question">생각 중인 동네나 업종을 알려주세요</label>
            <div className={styles.searchBox}>
              <input
                id="startup-question"
                ref={inputRef}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="예: 서문시장 근처 카페, 예산 5천"
              />
              <button type="submit" disabled={!text.trim() || mutation.isPending}>
                {mutation.isPending ? "찾는 중…" : "찾아보기"}<span aria-hidden="true">↗</span>
              </button>
            </div>
          </form>

          <div className={styles.chips} aria-label="예시 질문">
            {EXAMPLE_CHIPS.map((chip) => (
              <button key={chip} type="button" onClick={() => { setText(chip); inputRef.current?.focus(); }} className={styles.chip}>
                {chip}
              </button>
            ))}
          </div>

          {mutation.isError && <p role="alert" className={styles.error}>요청을 처리하지 못했습니다. 다시 시도해 주세요.</p>}

          {awaitingIndustry && (
            <div className={styles.industryPrompt} aria-live="polite">
              <p>어떤 업종을 찾으세요?</p>
              <div className={styles.chips}>
                {Object.entries(INDUSTRY_LABELS).map(([id, label]) => (
                  <button key={id} type="button" onClick={() => handlePickIndustry(id)} className={styles.chip}>{label}</button>
                ))}
                <button type="button" onClick={handleSkipIndustry} className={styles.chip}>잘 몰라요 — 업종별 위험도 먼저 보기</button>
              </div>
            </div>
          )}

          <Link href="/map" className={styles.textLink}>지도에서 직접 둘러보기 <span aria-hidden="true">→</span></Link>
        </div>
        <HeroVisual />
      </section>

      <ol className={styles.steps} aria-label="창업 계획을 구체화하는 세 단계">
        <li><span className={styles.stepNumber}>01</span><div><h2>동네를 발견하고</h2><p>지도 위에서 상권과 업종 살펴보기</p></div><span className={styles.stepArrow} aria-hidden="true">↗</span></li>
        <li><span className={styles.stepNumber}>02</span><div><h2>자금을 계산하고</h2><p>내 조건으로 준비자금과 조달 필요 확인하기</p></div><span className={styles.stepArrow} aria-hidden="true">↗</span></li>
        <li><span className={styles.stepNumber}>03</span><div><h2>상담을 준비해요</h2><p>바꾼 계획과 물어볼 것을 정리해 은행 상담으로</p></div></li>
      </ol>

      <section className={styles.features} aria-labelledby="features-title">
        <div className={styles.sectionHeading}><div><p className={styles.sectionLabel}>작은 시작, 구체적인 계획</p><h2 id="features-title">내 가게의 가능성,<br />한 걸음씩 확인하세요.</h2></div><p>동네를 고르는 순간부터 자금을 계획할 때까지.{" "}<br />창업에 필요한 질문을 하나씩 풀어갑니다.</p></div>
        <div className={styles.featureGrid}>
          <article className={styles.mapFeature}>
            <p className={styles.featureNumber}>01 / 상권 탐색</p>
            <h3>좋아하는 동네가<br />장사하기에도 좋을까?</h3>
            <p className={styles.featureDescription}>행정동별 상권 지표와 업종별 위험도를 비교하며<br className={styles.desktopBreak} /> 내 가게가 자리 잡을 동네를 찾아보세요.</p>
            <Link href="/map" className={styles.featureLink}>상권 지도 살펴보기 <span aria-hidden="true">↗</span></Link>
            <p className={styles.mapDisclaimer}>이해를 돕기 위한 지도 모식도입니다.</p>
            <div className={styles.mapPreview}>
              <div className={styles.previewToolbar}><span><i aria-hidden="true" />대구 상권 지도</span><span className={styles.sampleBadge}>예시</span></div>
              <svg viewBox="0 0 540 260" fill="none" aria-hidden="true" className={styles.districtMap}>
                <path d="M-20 22L123 4L193 68L173 143L48 163L-20 115Z" fill="var(--bg-raised)" />
                <path d="M140 0L323 -12L310 94L204 112L194 60Z" fill="var(--brand-soft)" />
                <path d="M327 -10L520 0L556 108L447 141L321 91Z" fill="var(--bg-raised)" />
                <path d="M186 147L212 122L309 104L385 139L363 220L256 254L163 218Z" fill="var(--brand-mint)" fillOpacity=".58" stroke="var(--accent)" strokeWidth="1.5" />
                <path d="M-15 176L151 157L150 231L246 272L-12 281Z" fill="var(--brand-soft)" />
                <path d="M399 151L548 117L554 280L361 271L377 222Z" fill="var(--brand-soft)" />
                <path d="M-10 94C95 52 98 230 220 191S336 108 550 190" stroke="var(--bg-surface)" strokeWidth="12" />
                <path d="M276 -5L250 88L294 169L265 267" stroke="var(--bg-surface)" strokeWidth="8" />
                <g fill="var(--text-secondary)" fontSize="14" fontFamily="inherit"><text x="105" y="100">서구</text><text x="244" y="55">북구</text><text x="445" y="83">동구</text><text x="105" y="223">달서구</text><text x="426" y="231">수성구</text></g>
                <circle cx="276" cy="148" r="12" fill="var(--brand-ink)" stroke="white" strokeWidth="5" />
              </svg>
              <div className={styles.mapCallout}><span>중구 · 카페</span><strong>동네마다 다른 가능성</strong><p>밀집도 · 개폐업 · 성장 지표 비교</p></div>
            </div>
          </article>

          <article className={styles.financeFeature}>
            <div><p className={styles.featureNumber}>02 / 자금 계획</p><h3>내 예산으로<br />어디까지 가능할까?</h3><p className={styles.featureDescription}>보증금부터 운영비까지,<br />필요한 자금을 직접 계산해 보세요.</p><Link href="/simulate" className={styles.featureLink}>창업 비용 계산하기 <span aria-hidden="true">↗</span></Link></div>
            <div className={styles.budgetPreview}><div><span>창업 예산</span><span className={styles.sampleBadge}>예시</span></div><strong>5,000<span>만 원</span></strong><div className={styles.budgetBar} aria-hidden="true"><i /><i /><i /></div><p><span>보증금</span><span>시설비</span><span>운영비</span></p></div>
          </article>

          <article className={styles.evidenceFeature}>
            <p className={styles.featureNumber}>03 / 근거 확인</p>
            <h3>숫자만큼 중요한,<br />숫자 뒤의 기준.</h3>
            <p className={styles.featureDescription}>지표의 뜻과 출처를 함께 살펴보고,<br />내 상황에 맞는 판단을 준비하세요.</p>
            <Link href="/map" className={styles.featureLink}>상권 지표 확인하기 <span aria-hidden="true">↗</span></Link>
            <div className={styles.evidenceMark} aria-hidden="true"><span>↗</span><span>≡</span></div>
          </article>
        </div>
      </section>

      <footer className={styles.footer}><div><strong>localhostdaegu<span>.</span></strong><p>대구에서 시작하는 당신의 다음 계획.</p></div><span>대구 창업 금융 네비게이터</span><Link href="/map">상권 둘러보기 <span aria-hidden="true">↗</span></Link></footer>
    </main>
  );
}

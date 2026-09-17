import Image from "next/image";
import styles from "./chat-landing.module.css";

export function HeroVisual() {
  return (
    <div className={styles.heroVisual}>
      <div className={styles.visualHalo} aria-hidden="true" />
      <svg className={styles.heroMap} viewBox="0 0 560 440" fill="none" aria-hidden="true">
        <path d="M22 268L205 181L531 278L343 394Z" fill="var(--brand-soft)" stroke="var(--border)" />
        <path d="M78 241L395 358M143 211L459 320M93 299L269 205M181 333L363 233M271 368L455 260" stroke="var(--bg-surface)" strokeWidth="9" />
        <path d="M78 241L395 358M143 211L459 320M93 299L269 205M181 333L363 233M271 368L455 260" stroke="var(--border)" strokeWidth="1" />
        <path d="M92 298L183 333L362 233" stroke="var(--accent)" strokeWidth="2" strokeDasharray="5 6" />
        <circle cx="92" cy="298" r="7" fill="var(--brand-mint)" stroke="var(--bg-surface)" strokeWidth="3" />
        <ellipse cx="297" cy="279" rx="74" ry="19" fill="var(--brand-ink)" fillOpacity=".09" />
      </svg>
      <Image src="/brand/brand-pin.png" alt="" width={960} height={1080} sizes="(max-width: 600px) 80vw, 440px" loading="eager" className={styles.brandPin} />
      <div className={`${styles.previewCard} ${styles.locationCard}`}>
        <div className={styles.previewCardHeading}><span className={styles.locationIcon} aria-hidden="true">⌖</span><span>내가 궁금한 상권</span><span className={styles.sampleBadge}>예시</span></div>
        <strong>중구 <span>·</span> 카페</strong>
        <p>밀집도부터 개폐업 현황까지</p>
        <div className={styles.miniChart} aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /><i /><i /></div>
        <div className={styles.cardCaption}><span>동네 비교</span><span>업종 탐색</span></div>
      </div>
      <div className={`${styles.previewCard} ${styles.fundingCard}`}>
        <div className={styles.previewCardHeading}><span>나의 시작 자금</span><span className={styles.sampleBadge}>예시</span></div>
        <strong>5,000<span>만 원</span></strong>
        <div className={styles.fundingRule} aria-hidden="true"><span /></div>
        <p>내 예산에서 출발하는 창업 계획</p>
      </div>
      <p className={styles.visualCaption}><span aria-hidden="true">✳</span> 가능성이 시작되는 곳, 대구</p>
    </div>
  );
}

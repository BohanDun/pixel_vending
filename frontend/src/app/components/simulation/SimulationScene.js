"use client";

import { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import styles from './SimulationScene.module.css';


const COLOR_MAP = {
  light: '#f6c89f',
  medium: '#c98b5a',
  dark: '#754c2f',
  black: '#202124',
  brown: '#6f4426',
  blonde: '#f2cc60',
  red: '#b54b36',
  blue: '#3977d5',
  green: '#2ea66f',
  yellow: '#f3c94b',
  purple: '#8759c7',
  navy: '#24365f',
  grey: '#707985',
};

const CHARACTER_SHEETS = {
  Mia: '/assets/characters/mia-sheet.png',
  Ava: '/assets/characters/ava-sheet.png',
  Leo: '/assets/characters/leo-sheet.png',
  Jack: '/assets/characters/jack-sheet.png',
  Liam: '/assets/characters/jack-sheet.png',
  Sophie: '/assets/characters/sophie-sheet.png',
  Emma: '/assets/characters/emma-sheet.png',
  Noah: '/assets/characters/noah-sheet.png',
};

function PixelCustomer({ customer, phase, targetX }) {
  if (!customer) return null;

  const customerStyle = {
    '--character-sheet': `url("${CHARACTER_SHEETS[customer.name] || CHARACTER_SHEETS.Mia}")`,
    '--customer-target': targetX == null ? '40%' : `${targetX}px`,
  };

  return (
    <div className={`${styles.customerWrap} ${styles[phase]}`} style={customerStyle}>
      <div className={styles.nameTag}>{customer.name}</div>
      <div className={styles.pixelPerson} aria-label={`${customer.name}, pixel customer`}>
        <div className={styles.characterShadow} />
        <div className={styles.characterSprite} />
      </div>
    </div>
  );
}


function PixelMachine({ machine, active, index }) {
  const stockedUnits = (machine.products || []).reduce(
    (total, product) => total + Number(product.machine_quantity || 0),
    0
  );

  return (
    <div
      className={`${styles.machineStation} ${active ? styles.activeMachine : ''}`}
      data-machine-id={machine.id}
    >
      <div className={styles.machine} aria-label={`Pixel vending machine ${machine.name}`}>
        <Image
          className={styles.machineSprite}
          src="/assets/sprites/vending-machine.png"
          alt=""
          width={192}
          height={289}
          unoptimized
        />
        <i className={stockedUnits > 0 ? styles.stockLight : styles.emptyLight} />
        <span className={styles.machineNumber}>
          {String(index + 1).padStart(2, '0')}
        </span>
      </div>
      <span className={styles.machineName}>
        {machine.name}
        <small>{stockedUnits} units</small>
      </span>
    </div>
  );
}


export default function SimulationScene({
  running,
  machines,
  speed,
  phase,
  result,
  error,
  history,
  onStart,
  onPause,
  onSpeedChange,
  onRunOnce,
}) {
  const purchases = result?.purchases || [];
  const selectedMachineIds = new Set(
    purchases.map((purchase) => purchase.machine_id)
  );
  const successfulPurchases = purchases.filter(
    (purchase) => purchase.transaction.status === 'SUCCESS'
  );
  const allSuccessful =
    purchases.length > 0 && successfulPurchases.length === purchases.length;
  const sceneRef = useRef(null);
  const [customerTargetX, setCustomerTargetX] = useState(null);
  const targetMachineId = purchases[0]?.machine_id;

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || targetMachineId == null) {
      setCustomerTargetX(null);
      return undefined;
    }

    const updateCustomerTarget = () => {
      const machine = scene.querySelector(
        `[data-machine-id="${targetMachineId}"]`
      );
      if (!machine) return;

      const sceneBounds = scene.getBoundingClientRect();
      const machineBounds = machine.getBoundingClientRect();
      const desiredLeft = machineBounds.left - sceneBounds.left - 88;
      setCustomerTargetX(
        Math.max(72, Math.min(desiredLeft, sceneBounds.width - 130))
      );
    };

    const frameId = window.requestAnimationFrame(updateCustomerTarget);
    const observer = new ResizeObserver(updateCustomerTarget);
    observer.observe(scene);
    window.addEventListener('resize', updateCustomerTarget);

    return () => {
      window.cancelAnimationFrame(frameId);
      observer.disconnect();
      window.removeEventListener('resize', updateCustomerTarget);
    };
  }, [targetMachineId, machines.length]);

  return (
    <section className={styles.simulator}>
      <div className={styles.toolbar}>
        <div>
          <p className={styles.eyebrow}>LIVE STORE</p>
          <h2>Pixel Vending Simulator</h2>
        </div>
        <div className={styles.controls}>
          <button
            type="button"
            className={running ? styles.pauseButton : styles.startButton}
            onClick={running ? onPause : onStart}
          >
            {running ? 'Pause' : 'Start'}
          </button>
          <button type="button" className={styles.onceButton} onClick={onRunOnce}>
            Next customer
          </button>
          <label>
            Speed
            <select value={speed} onChange={(event) => onSpeedChange(Number(event.target.value))}>
              <option value={7000}>Slow</option>
              <option value={5000}>Normal</option>
              <option value={3500}>Fast</option>
            </select>
          </label>
        </div>
      </div>

      <div className={styles.contentGrid}>
        <div className={styles.scene} ref={sceneRef}>
          <div className={styles.sun} />
          <div className={styles.skyline}>
            {[0, 1, 2, 3].map((building) => (
              <span key={building}>
                <i /><i /><i /><i />
              </span>
            ))}
          </div>
          <div className={styles.storeWall}>
            <div className={styles.awning}>
              <span /><span /><span /><span /><span /><span /><span />
            </div>
            <div className={styles.storeHeader}>
              <span className={styles.spark}>✦</span>
              PIXEL MART
              <small>SNACKS · DRINKS · 24/7</small>
            </div>
            <div className={styles.wallTiles} />
          </div>
          <div className={styles.sign}>
            <i />
            OPEN 24/7
          </div>
          <div className={styles.poster}>
            <strong>COOL</strong>
            <span>DRINKS</span>
            <i>★</i>
          </div>
          <div className={styles.plant}>
            <i /><i /><i />
            <span />
          </div>
          <div className={styles.streetLamp}>
            <i />
            <span />
          </div>
          <PixelCustomer
            customer={result?.customer}
            phase={phase}
            targetX={customerTargetX}
          />
          <div className={styles.machineRow}>
            {machines.map((machine, index) => (
              <PixelMachine
                key={machine.id}
                machine={machine}
                active={selectedMachineIds.has(machine.id)}
                index={index}
              />
            ))}
          </div>

          {result && ['purchasing', 'completed', 'rejected'].includes(phase) && (
            <div className={`${styles.bubble} ${allSuccessful ? styles.success : styles.failure}`}>
              <strong>{result.customer.name}</strong>
              {purchases.map((purchase) => (
                <span key={purchase.transaction.id}>
                  {purchase.machine_name}: {purchase.quantity} × {purchase.product_name}
                  {' · '}
                  {purchase.transaction.status.replaceAll('_', ' ')}
                </span>
              ))}
              <small>Budget ${Number(result.customer.budget).toFixed(2)}</small>
            </div>
          )}
          {!result && (
            <div className={styles.emptyMessage}>
              <span>▶</span>
              Press Start to welcome the first customer.
            </div>
          )}
          <div className={styles.curb} />
          <div className={styles.floor} />
          <div className={styles.roadLine} />
        </div>

        <aside className={styles.activity}>
          <div className={styles.storeStatus}>
            <span>STORE STATUS</span>
            <strong><i /> OPEN 24/7</strong>
          </div>
          <div className={styles.activityHeader}>
            <h3>Activity feed</h3>
            <span className={running ? styles.live : styles.paused}>
              {running ? 'LIVE' : 'PAUSED'}
            </span>
          </div>
          {error && <div className={styles.error}>{error}</div>}
          {history.length === 0 ? (
            <p className={styles.noActivity}>No purchases yet.</p>
          ) : (
            <ol>
              {history.map((item) => (
                <li key={item.customer.customer_id}>
                  <span className={styles.avatarDot} style={{ background: COLOR_MAP[item.customer.sprite.shirt] }} />
                  <div>
                    <strong>{item.customer.name}</strong>
                    <small>
                      {item.purchases.map((purchase) => (
                        `${purchase.machine_name}: ${purchase.quantity}× ${purchase.product_name}`
                      )).join(', ')}
                    </small>
                  </div>
                  <span className={item.purchases.some((purchase) => purchase.transaction.status === 'SUCCESS') ? styles.okMark : styles.failMark}>
                    {item.purchases.some((purchase) => purchase.transaction.status === 'SUCCESS') ? '✓' : '×'}
                  </span>
                </li>
              ))}
            </ol>
          )}
          <div className={styles.quickActions}>
            <h3>Quick actions</h3>
            <button type="button" onClick={() => document.getElementById('inventory-controls')?.scrollIntoView({ behavior: 'smooth' })}>
              <span>＋</span> Add product
            </button>
            <button type="button" onClick={() => document.getElementById('reports')?.scrollIntoView({ behavior: 'smooth' })}>
              <span>▥</span> View reports
            </button>
            <button type="button" onClick={() => document.getElementById('machines')?.scrollIntoView({ behavior: 'smooth' })}>
              <span>⚙</span> Manage machines
            </button>
          </div>
        </aside>
      </div>
    </section>
  );
}

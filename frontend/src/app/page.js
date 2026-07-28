"use client";

import { useContext, useState, useEffect, useRef } from 'react';
import AuthContext from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import SimulationScene from './components/simulation/SimulationScene';
import axios from 'axios';

const delay = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

const TRANSACTIONS_PER_PAGE = 10;
const MAX_MACHINES = 4;
const MACHINE_LIMIT_MESSAGE = 'sorry, no availabe space';

const Home = () => {
  const { user, logout } = useContext(AuthContext);
  const [products, setProducts] = useState([]);
  const [machines, setMachines] = useState([]);
  const [dailySummaries, setDailySummaries] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [transactionStatus, setTransactionStatus] = useState('');
  const [transactionPage, setTransactionPage] = useState(0);
  const [transactionHasNext, setTransactionHasNext] = useState(false);
  const [transactionsLoading, setTransactionsLoading] = useState(false);
  const [productName, setProductName] = useState('');
  const [productDescription, setProductDescription] = useState('');
  const [productQuantity, setProductQuantity] = useState('');
  const [productPrice, setProductPrice] = useState('');
  const [machineName, setMachineName] = useState('');
  const [machineDescription, setMachineDescription] = useState('');
  const [selectedProducts, setSelectedProducts] = useState([]);
  const [selectedProductByMachine, setSelectedProductByMachine] = useState({});
  const [selectedProductQuantityByMachine, setSelectedProductQuantityByMachine] = useState({});
  const [deleteQuantityByMachineProduct, setDeleteQuantityByMachineProduct] = useState({});
  const [addQuantityByMachineProduct, setAddQuantityByMachineProduct] = useState({});
  const [putBackQuantityByMachineProduct, setPutBackQuantityByMachineProduct] = useState({});
  const [restockQuantityByProduct, setRestockQuantityByProduct] = useState({});
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [simulationSpeed, setSimulationSpeed] = useState(5000);
  const [simulationPhase, setSimulationPhase] = useState('idle');
  const [simulationResult, setSimulationResult] = useState(null);
  const [simulationHistory, setSimulationHistory] = useState([]);
  const [simulationError, setSimulationError] = useState('');
  const simulationBusy = useRef(false);
  const manualActionPending = useRef(false);

  const getErrorMessage = (error, fallback) => error?.response?.data?.detail || fallback;

  const handleApiError = (error, fallback, showAlert = true) => {
    const message = getErrorMessage(error, fallback);
    if (error?.response?.status === 401) {
      setSimulationRunning(false);
      window.alert('Your login session has expired. Please log in again.');
      logout();
      return message;
    }
    if (showAlert) window.alert(message);
    return message;
  };

  const getAuth = () => {
    const raw = sessionStorage.getItem('token');
    if (!raw) return {};
    let token = raw;
    try {
      const parsed = JSON.parse(raw);
      token = parsed.access_token ?? parsed.token ?? raw;
    } catch {}
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  useEffect(() => {
    const fetchProductsAndMachines = async () => {
      try {
        const raw = sessionStorage.getItem('token');
        if (!raw) return;
        let token = raw;
        try {
          const parsed = JSON.parse(raw);
          token = parsed.access_token ?? parsed.token ?? raw;
        } catch {}
        const auth = { headers: { Authorization: `Bearer ${token}` } };

        const [
          productsResponse,
          machinesResponse,
          dailySummariesResponse,
        ] = await Promise.all([
          axios.get('http://localhost:8000/products/', auth),
          axios.get('http://localhost:8000/machines/', auth),
          axios.get('http://localhost:8000/daily-summaries/', auth),
        ]);
        setProducts(productsResponse.data);
        setMachines(machinesResponse.data);
        setDailySummaries(dailySummariesResponse.data);
      } catch (error) {
        handleApiError(error, 'Failed to load inventory data');
      }
    };

    fetchProductsAndMachines();
  }, []);

  const refreshProductsAndMachines = async () => {
    const auth = getAuth();
    const [productsResponse, machinesResponse] = await Promise.all([
      axios.get('http://localhost:8000/products/', auth),
      axios.get('http://localhost:8000/machines/', auth),
    ]);
    setProducts(productsResponse.data);
    setMachines(machinesResponse.data);
  };

  const fetchTransactions = async (
    page = transactionPage,
    status = transactionStatus
  ) => {
    if (!sessionStorage.getItem('token')) return;

    setTransactionsLoading(true);
    try {
      const response = await axios.get(
        'http://localhost:8000/transactions/',
        {
          ...getAuth(),
          params: {
            limit: TRANSACTIONS_PER_PAGE,
            offset: page * TRANSACTIONS_PER_PAGE,
            ...(status ? { transaction_status: status } : {}),
          },
        }
      );
      setTransactions(response.data);
      setTransactionHasNext(
        response.data.length === TRANSACTIONS_PER_PAGE
      );
    } catch (error) {
      handleApiError(error, 'Failed to load transaction history');
    } finally {
      setTransactionsLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions(transactionPage, transactionStatus);
  }, [transactionPage, transactionStatus]);

  const formatTransactionTime = (value) => {
    if (!value) return '—';
    const normalized = /Z$|[+-]\d{2}:\d{2}$/.test(value)
      ? value
      : `${value}Z`;
    return new Intl.DateTimeFormat('en-NZ', {
      timeZone: 'Pacific/Auckland',
      dateStyle: 'medium',
      timeStyle: 'medium',
    }).format(new Date(normalized));
  };

  const productNameForTransaction = (transaction) =>
    products.find((product) => product.id === transaction.product_id)?.name
    || (transaction.product_id == null ? 'Deleted product' : `Product #${transaction.product_id}`);

  const machineNameForTransaction = (transaction) =>
    machines.find((machine) => machine.id === transaction.machine_id)?.name
    || (transaction.machine_id == null ? 'Deleted machine' : `Machine #${transaction.machine_id}`);

  const runSimulationOnce = async () => {
    if (simulationBusy.current || manualActionPending.current) return;

    simulationBusy.current = true;
    setSimulationError('');
    try {
      const response = await axios.post(
        'http://localhost:8000/simulation/run-once',
        {},
        {
          ...getAuth(),
          timeout: 10000,
        }
      );
      const result = response.data;
      setSimulationResult(result);
      setSimulationHistory((previous) => [result, ...previous].slice(0, 6));

      setSimulationPhase('entering');
      await delay(350);
      setSimulationPhase('walking');
      await delay(800);
      setSimulationPhase('purchasing');
      await delay(650);
      setSimulationPhase(
        result.purchases.every(
          (purchase) => purchase.transaction.status === 'SUCCESS'
        )
          ? 'completed'
          : 'rejected'
      );
      await delay(750);
      setSimulationPhase('leaving');
      await delay(700);
      setSimulationPhase('idle');
      await refreshProductsAndMachines();
      if (transactionPage === 0) {
        await fetchTransactions(0, transactionStatus);
      }
    } catch (error) {
      if (error?.response?.status === 401) {
        handleApiError(error, 'Your login session has expired');
        return;
      }
      setSimulationError(
        getErrorMessage(
          error,
          'Simulation could not run. Add a machine with stocked products first.'
        )
      );
      setSimulationRunning(false);
      setSimulationPhase('idle');
    } finally {
      simulationBusy.current = false;
    }
  };

  const pauseSimulationForManualAction = async () => {
    manualActionPending.current = true;
    setSimulationRunning(false);

    while (simulationBusy.current) {
      await delay(50);
    }
  };

  const finishManualAction = () => {
    manualActionPending.current = false;
  };

  useEffect(() => {
    if (!simulationRunning) return undefined;

    runSimulationOnce();
    const intervalId = window.setInterval(
      runSimulationOnce,
      simulationSpeed
    );
    return () => window.clearInterval(intervalId);
  }, [simulationRunning, simulationSpeed]);

  const handleCreateProduct = async (e) => {
    e.preventDefault();
    try {
      await axios.post(
        'http://localhost:8000/products/',
        {
          name: productName,
          description: productDescription,
          quantity: Number(productQuantity),
          price: productPrice,
        },
        getAuth()
      );
      setProductName('');
      setProductDescription('');
      setProductQuantity('');
      setProductPrice('');
      await refreshProductsAndMachines();
    } catch (error) {
      handleApiError(error, 'Failed to create product');
    }
  };

  const handleCreateMachine = async (e) => {
    e.preventDefault();
    if (machines.length >= MAX_MACHINES) {
      window.alert(MACHINE_LIMIT_MESSAGE);
      return;
    }

    try {
      await axios.post(
        'http://localhost:8000/machines/',
        { name: machineName, description: machineDescription, products: selectedProducts.map(Number) },
        getAuth()
      );
      setMachineName('');
      setMachineDescription('');
      setSelectedProducts([]);
      await refreshProductsAndMachines();
    } catch (error) {
      handleApiError(error, 'Failed to create machine');
    }
  };

  const deleteProduct = async (id) => {
    try {
      await axios.delete(`http://localhost:8000/products/${id}`, getAuth());
      setProducts((prev) => prev.filter((product) => product.id !== id));
      setSelectedProducts((prev) => prev.filter((productId) => productId !== id));
      setMachines((prev) =>
        prev.map((machine) => ({
          ...machine,
          products: (machine.products || []).filter((product) => product.id !== id),
        }))
      );
    } catch (error) {
      handleApiError(error, 'Failed to delete product');
    }
  };

  const deleteMachine = async (id) => {
    try {
      await axios.delete(`http://localhost:8000/machines/${id}`, getAuth());
      await refreshProductsAndMachines();
    } catch (error) {
      handleApiError(error, 'Failed to delete machine');
    }
  };

  const addProductToMachine = async (machineId) => {
    const productId = selectedProductByMachine[machineId];

    if (!productId) return;

    await pauseSimulationForManualAction();
    try {
      await axios.post(
        `http://localhost:8000/machines/${machineId}/products/${productId}`,
        { quantity: Number(selectedProductQuantityByMachine[machineId] || 0) },
        getAuth()
      );

      await refreshProductsAndMachines();

      setSelectedProductByMachine((prev) => ({
        ...prev,
        [machineId]: '',
      }));
      setSelectedProductQuantityByMachine((prev) => ({
        ...prev,
        [machineId]: '',
      }));
    } catch (error) {
      handleApiError(error, 'Failed to add product to machine');
    } finally {
      finishManualAction();
    }
  };

  const removeProductFromMachine = async (machineId, productId) => {
    try {
      await axios.delete(
        `http://localhost:8000/machines/${machineId}/products/${productId}`,
        getAuth()
      );

      await refreshProductsAndMachines();
    } catch (error) {
      handleApiError(error, 'Failed to remove product from machine');
    }
  };

  const deleteMachineProductQuantity = async (machineId, productId) => {
    const key = `${machineId}-${productId}`;
    const quantity = Number(deleteQuantityByMachineProduct[key] || 0);

    if (quantity <= 0) return;

    try {
      await axios.post(
        `http://localhost:8000/machines/${machineId}/products/${productId}/delete-quantity`,
        { quantity },
        getAuth()
      );
      await refreshProductsAndMachines();
      setDeleteQuantityByMachineProduct((prev) => ({
        ...prev,
        [key]: '',
      }));
    } catch (error) {
      handleApiError(error, 'Failed to sell product quantity');
    }
  };

  const addMachineProductQuantity = async (machineId, product) => {
    const key = `${machineId}-${product.id}`;
    const quantity = Number(addQuantityByMachineProduct[key] || 0);

    if (quantity <= 0) return;

    await pauseSimulationForManualAction();
    try {
      await axios.put(
        `http://localhost:8000/machines/${machineId}/products/${product.id}/quantity`,
        { quantity: (product.machine_quantity || 0) + quantity },
        getAuth()
      );
      await refreshProductsAndMachines();
      setAddQuantityByMachineProduct((prev) => ({
        ...prev,
        [key]: '',
      }));
    } catch (error) {
      handleApiError(error, 'Failed to add machine product quantity');
    } finally {
      finishManualAction();
    }
  };

  const putBackMachineProductQuantity = async (machineId, productId) => {
    const key = `${machineId}-${productId}`;
    const quantity = Number(putBackQuantityByMachineProduct[key] || 0);

    if (quantity <= 0) return;

    try {
      await axios.post(
        `http://localhost:8000/machines/${machineId}/products/${productId}/put-back`,
        { quantity },
        getAuth()
      );
      await refreshProductsAndMachines();
      setPutBackQuantityByMachineProduct((prev) => ({
        ...prev,
        [key]: '',
      }));
    } catch (error) {
      handleApiError(error, 'Failed to put product back in warehouse');
    }
  };

  const updateProductPrice = async (productId, price) => {
    try {
      await axios.put(
        `http://localhost:8000/products/${productId}/price`,
        { price },
        getAuth()
      );
      await refreshProductsAndMachines();
    } catch (error) {
      handleApiError(error, 'Failed to update product price');
    }
  };

  const restockProduct = async (productId) => {
    const quantity = Number(restockQuantityByProduct[productId] || 0);

    if (quantity <= 0) return;

    await pauseSimulationForManualAction();
    try {
      await axios.post(
        `http://localhost:8000/products/${productId}/restock`,
        { quantity },
        getAuth()
      );
      await refreshProductsAndMachines();
      setRestockQuantityByProduct((prev) => ({
        ...prev,
        [productId]: '',
      }));
    } catch (error) {
      handleApiError(error, 'Failed to restock product');
    } finally {
      finishManualAction();
    }
  };

  const clearTransactionHistory = async () => {
    const confirmed = window.confirm(
      'Clear all detailed transaction records for this account? '
      + 'Today’s unsettled sales will no longer be included in the next daily summary. '
      + 'Existing daily summaries will be kept. This cannot be undone.'
    );
    if (!confirmed) return;

    await pauseSimulationForManualAction();
    try {
      await axios.delete(
        'http://localhost:8000/transactions/',
        getAuth()
      );
      setTransactions([]);
      setSimulationHistory([]);
      setTransactionPage(0);
      setTransactionHasNext(false);
    } catch (error) {
      handleApiError(error, 'Failed to clear transaction history');
    } finally {
      finishManualAction();
    }
  };

  const warehouseUnits = products.reduce(
    (total, product) => total + Number(product.quantity || 0),
    0
  );
  const machineUnits = products.reduce(
    (total, product) => total + Number(product.machine_quantity_total || 0),
    0
  );
  const settledRevenue = dailySummaries.reduce(
    (total, summary) => total + Number(summary.total_revenue || 0),
    0
  );
  const chartSummaries = [...dailySummaries].slice(0, 7).reverse();
  const chartMaximum = Math.max(
    1,
    ...chartSummaries.map((summary) => Number(summary.total_revenue || 0))
  );

  return (
    <ProtectedRoute>
      <main className="app-shell">
        <header className="app-header">
          <div className="brand-lockup">
            <img
              className="header-brand-logo"
              src="/assets/pixel-vending-header-logo.png"
              alt="Pixel Vending Simulator"
            />
          </div>
          <div className="header-account">
            <span className="system-indicator">
              <i />
              AUTO MODE
            </span>
            <span className="account-name">{user?.username || 'Operator'}</span>
            <button onClick={logout} className="btn btn-sm btn-outline-danger">
              Log out
            </button>
          </div>
        </header>

        <div className="dashboard-container">
          <section className="hero-row">
            <div>
              <span className="section-kicker">STORE OVERVIEW</span>
              <h1>Store control room</h1>
              <p>Keep the shelves full, watch customers shop and grow your tiny store.</p>
            </div>
            <div className="hero-date">
              <span>Local timezone</span>
              <strong>Pacific / Auckland</strong>
            </div>
          </section>

          <section className="metric-grid" aria-label="Store metrics">
            <article className="metric-card metric-blue">
              <span className="metric-icon metric-machine" aria-hidden="true" />
              <div><small>Machines</small><strong>{machines.length}</strong></div>
              <em>registered</em>
            </article>
            <article className="metric-card metric-violet">
              <span className="metric-icon metric-product" aria-hidden="true" />
              <div><small>Products</small><strong>{products.length}</strong></div>
              <em>catalogue items</em>
            </article>
            <article className="metric-card metric-green">
              <span className="metric-icon metric-stock" aria-hidden="true" />
              <div><small>Machine stock</small><strong>{machineUnits}</strong></div>
              <em>{warehouseUnits} in warehouse</em>
            </article>
            <article className="metric-card metric-amber">
              <span className="metric-icon metric-coin" aria-hidden="true" />
              <div><small>30-day revenue</small><strong>${settledRevenue.toFixed(2)}</strong></div>
              <em>{dailySummaries.length} settled days</em>
            </article>
          </section>

          <SimulationScene
            running={simulationRunning}
            machines={machines}
            speed={simulationSpeed}
            phase={simulationPhase}
            result={simulationResult}
            error={simulationError}
            history={simulationHistory}
            onStart={() => setSimulationRunning(true)}
            onPause={() => setSimulationRunning(false)}
            onSpeedChange={setSimulationSpeed}
            onRunOnce={runSimulationOnce}
          />

        <div className="analytics-grid">
        <section className="dashboard-panel mb-4" id="reports">
          <div className="d-flex align-items-center justify-content-between mb-3">
            <div>
              <h3 className="mb-1">Last 30 days</h3>
              <small className="text-body-secondary">
                Daily sales summaries · Pacific/Auckland
              </small>
            </div>
            <span className="badge text-bg-secondary">
              {dailySummaries.length} settled days
            </span>
          </div>

          {chartSummaries.length > 0 && (
            <div className="sales-chart" aria-label="Revenue for the last seven settled days">
              <div className="chart-scale">
                <span>${chartMaximum.toFixed(0)}</span>
                <span>${(chartMaximum / 2).toFixed(0)}</span>
                <span>$0</span>
              </div>
              <div className="chart-bars">
                {chartSummaries.map((summary) => {
                  const revenue = Number(summary.total_revenue || 0);
                  return (
                    <div className="chart-column" key={summary.id}>
                      <span
                        className="chart-bar"
                        style={{ height: `${Math.max(4, (revenue / chartMaximum) * 100)}%` }}
                        title={`${summary.summary_date}: $${revenue.toFixed(2)}`}
                      />
                      <small>{summary.summary_date.slice(5)}</small>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {dailySummaries.length === 0 ? (
            <div className="alert alert-secondary mb-0" role="status">
              No settled sales days yet. The first summary is created after
              midnight, or on the next backend startup.
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-sm align-middle">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Revenue</th>
                    <th>Successful</th>
                    <th>Failed</th>
                    <th>Units sold</th>
                    <th>Top product</th>
                  </tr>
                </thead>
                <tbody>
                  {dailySummaries.map((summary) => (
                    <tr key={summary.id}>
                      <td>{summary.summary_date}</td>
                      <td>${Number(summary.total_revenue).toFixed(2)}</td>
                      <td>{summary.successful_transactions}</td>
                      <td>{summary.failed_transactions}</td>
                      <td>{summary.units_sold}</td>
                      <td>
                        {summary.top_product_id == null
                          ? '—'
                          : `Product #${summary.top_product_id}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="dashboard-panel mb-4">
          <div className="d-flex flex-wrap align-items-end justify-content-between gap-3 mb-3">
            <div>
              <h3 className="mb-1">Recent 7-day transactions</h3>
              <small className="text-body-secondary">
                Persistent purchase records · Pacific/Auckland time
              </small>
            </div>
            <div className="d-flex align-items-center gap-2">
              <label className="d-flex align-items-center gap-2">
                <span className="text-body-secondary">Status</span>
                <select
                  className="form-select form-select-sm"
                  value={transactionStatus}
                  onChange={(event) => {
                    setTransactionPage(0);
                    setTransactionStatus(event.target.value);
                  }}
                >
                  <option value="">All</option>
                  <option value="SUCCESS">Success</option>
                  <option value="OUT_OF_STOCK">Out of stock</option>
                  <option value="INSUFFICIENT_BUDGET">Insufficient budget</option>
                </select>
              </label>
              <button
                type="button"
                className="btn btn-sm btn-outline-danger text-nowrap"
                onClick={clearTransactionHistory}
                disabled={transactionsLoading}
              >
                Clear records
              </button>
            </div>
          </div>

          {transactionsLoading ? (
            <div className="alert alert-secondary">Loading transactions…</div>
          ) : transactions.length === 0 ? (
            <div className="alert alert-secondary">
              No transactions match this filter.
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-sm table-hover align-middle">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Customer</th>
                    <th>Machine</th>
                    <th>Product</th>
                    <th>Qty</th>
                    <th>Total</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((transaction) => (
                    <tr key={transaction.id}>
                      <td className="text-nowrap">
                        {formatTransactionTime(transaction.created_at)}
                      </td>
                      <td>{transaction.customer_id}</td>
                      <td>{machineNameForTransaction(transaction)}</td>
                      <td>{productNameForTransaction(transaction)}</td>
                      <td>{transaction.quantity}</td>
                      <td>
                        {transaction.total_price == null
                          ? '—'
                          : `$${Number(transaction.total_price).toFixed(2)}`}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            transaction.status === 'SUCCESS'
                              ? 'text-bg-success'
                              : 'text-bg-danger'
                          }`}
                          title={transaction.failure_reason || ''}
                        >
                          {transaction.status.replaceAll('_', ' ')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="d-flex align-items-center justify-content-between mt-3">
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              disabled={transactionPage === 0 || transactionsLoading}
              onClick={() => setTransactionPage((page) => page - 1)}
            >
              Previous
            </button>
            <span className="text-body-secondary">
              Page {transactionPage + 1}
            </span>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              disabled={!transactionHasNext || transactionsLoading}
              onClick={() => setTransactionPage((page) => page + 1)}
            >
              Next
            </button>
          </div>
        </section>
        </div>

        <section className="management-section" id="inventory-controls">
          <div className="section-heading">
            <div>
              <span className="section-kicker">STORE MANAGEMENT</span>
              <h2>Stock room</h2>
            </div>
            <p>Create catalogue items, configure machines and move stock.</p>
          </div>

        <div className="management-columns mb-5">
        <div className="creation-grid">
          <section className="creation-panel product-creation-panel" aria-labelledby="create-product-title">
            <h3 className="creation-panel-title" id="create-product-title">
              Create Product
            </h3>
            <div className="creation-panel-body">
              <form onSubmit={handleCreateProduct}>
                <div className="mb-3">
                  <label htmlFor="productName" className="form-label">Product Name</label>
                  <input
                    type="text"
                    className="form-control"
                    id="productName"
                    value={productName}
                    onChange={(e) => setProductName(e.target.value)}
                    required
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="productDescription" className="form-label">Product Description</label>
                  <input
                    type="text"
                    className="form-control"
                    id="productDescription"
                    value={productDescription}
                    onChange={(e) => setProductDescription(e.target.value)}
                    required
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="productQuantity" className="form-label">Quantity</label>
                  <input
                    type="number"
                    className="form-control"
                    id="productQuantity"
                    value={productQuantity}
                    onChange={(e) => setProductQuantity(e.target.value)}
                    min="0"
                    step="1"
                    required
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="productPrice" className="form-label">Price</label>
                  <input
                    type="number"
                    className="form-control"
                    id="productPrice"
                    value={productPrice}
                    onChange={(e) => setProductPrice(e.target.value)}
                    min="0"
                    step="0.01"
                    required
                  />
                </div>
                <button type="submit" className="btn btn-primary">Create Product</button>
              </form>
            </div>
          </section>

          <section className="creation-panel machine-creation-panel" aria-labelledby="create-machine-title">
            <h3 className="creation-panel-title" id="create-machine-title">
              Create Machine
            </h3>
            <div className="creation-panel-body">
              <form onSubmit={handleCreateMachine}>
                <div className="mb-3">
                  <label htmlFor="machineName" className="form-label">Machine Name</label>
                  <input
                    type="text"
                    className="form-control"
                    id="machineName"
                    value={machineName}
                    onChange={(e) => setMachineName(e.target.value)}
                    required
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="machineDescription" className="form-label">Machine Description</label>
                  <input
                    type="text"
                    className="form-control"
                    id="machineDescription"
                    value={machineDescription}
                    onChange={(e) => setMachineDescription(e.target.value)}
                    required
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="productSelect" className="form-label">Select Products</label>
                  <select
                    multiple
                    className="form-control"
                    id="productSelect"
                    value={selectedProducts}
                    onChange={(e) => setSelectedProducts([...e.target.selectedOptions].map(o => Number(o.value)))}
                  >
                    {products.map(product => (
                      <option key={product.id} value={product.id}>
                        {product.name}
                      </option>
                    ))}
                  </select>
                </div>
                <button type="submit" className="btn btn-primary">Create Machine</button>
              </form>
            </div>
          </section>
        </div>

        <div className="dashboard-panel product-list-panel">
          <div className="d-flex align-items-center justify-content-between mb-3">
            <h3 className="mb-0">Your products:</h3>
            <span className="badge text-bg-secondary">{products.length} registered</span>
          </div>

          {products.length === 0 ? (
            <div className="alert alert-secondary mb-0" role="status">
              No products registered for this account yet.
            </div>
          ) : (
            <div className="list-group">
              {products.map((product) => (
                <div
                  className="list-group-item d-flex align-items-start justify-content-between gap-3"
                  key={product.id}
                >
                  <div>
                    <h5 className="mb-3">
                      {product.description ? `${product.name}: ${product.description}` : product.name}
                    </h5>
                    <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
                      <label className="d-flex align-items-center gap-2 text-body-secondary">
                        <span>Price:</span>
                        <input
                          type="number"
                          className="form-control form-control-sm"
                          style={{ maxWidth: '120px' }}
                          min="0"
                          step="0.01"
                          defaultValue={Number(product.price).toFixed(2)}
                          onBlur={(e) => updateProductPrice(product.id, e.target.value)}
                        />
                      </label>
                    </div>
                    <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
                      <span className="text-body-secondary me-2">
                        Total quantity: {Number(product.quantity || 0) + Number(product.machine_quantity_total || 0)}
                      </span>
                      <input
                        type="number"
                        className="form-control form-control-sm"
                        style={{ maxWidth: '120px' }}
                        min="1"
                        step="1"
                        placeholder="Restock qty"
                        value={restockQuantityByProduct[product.id] || ''}
                        onChange={(e) =>
                          setRestockQuantityByProduct((prev) => ({
                            ...prev,
                            [product.id]: e.target.value,
                          }))
                        }
                      />
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-success"
                        onClick={() => restockProduct(product.id)}
                        disabled={!restockQuantityByProduct[product.id]}
                      >
                        Restock
                      </button>
                    </div>
                    <div className="d-flex flex-wrap gap-3 mb-1">
                      <small className="text-body-secondary">
                        Warehouse: {product.quantity || 0}
                      </small>
                      <small className="text-body-secondary">
                        In machines: {product.machine_quantity_total || 0}
                      </small>
                    </div>
                    {(product.machine_quantities || []).length === 0 ? (
                      <small className="text-body-secondary">Not assigned to any machine</small>
                    ) : (
                      <ul className="mb-0 ps-3">
                        {(product.machine_quantities || []).map((machineQuantity) => (
                          <li className="text-body-secondary" key={machineQuantity.machine_id}>
                            <small>
                              {machineQuantity.machine_name}: {machineQuantity.quantity}
                            </small>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-danger flex-shrink-0"
                    onClick={() => deleteProduct(product.id)}
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="dashboard-panel machine-list-panel" id="machines">
          <div className="d-flex align-items-center justify-content-between mb-3">
            <h3 className="mb-0">Your machines:</h3>
            <span className="badge text-bg-secondary">{machines.length} registered</span>
          </div>

          {machines.length === 0 ? (
            <div className="alert alert-secondary mb-0" role="status">
              No machines registered for this account yet.
            </div>
          ) : (
            <div className="d-flex flex-column gap-3">
              {machines.map(machine => (
              <div className="card" key={machine.id}>
                <div className="card-body">
                  <button type="button" className="btn btn-sm btn-outline-danger float-end" onClick={() => deleteMachine(machine.id)}>Delete</button>
                  <h5 className="card-title">{machine.name}</h5>
                  <p className="card-text">{machine.description}</p>
                  <ul className="card-text">
                    {machine.products && machine.products.map(product => (
                      <li key={product.id}>
                        <div className="d-flex flex-wrap align-items-center gap-2">
                          <span>
                            Price: ${Number(product.price).toFixed(2)}, {product.name}: {product.description} - Warehouse: {product.quantity || 0}, In this machine: {product.machine_quantity || 0}
                          </span>
                        </div>
                        <div className="d-flex flex-column gap-2 mt-2 mb-3">
                          <div className="d-flex flex-wrap align-items-center gap-2">
                            <input
                              type="number"
                              className="form-control form-control-sm"
                              style={{ maxWidth: '120px' }}
                              min="1"
                              max={product.quantity || 0}
                              step="1"
                              placeholder="Add qty"
                              value={addQuantityByMachineProduct[`${machine.id}-${product.id}`] || ''}
                              onChange={(e) =>
                                setAddQuantityByMachineProduct((prev) => ({
                                  ...prev,
                                  [`${machine.id}-${product.id}`]: e.target.value,
                                }))
                              }
                            />
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-success"
                              onClick={() => addMachineProductQuantity(machine.id, product)}
                              disabled={
                                !addQuantityByMachineProduct[`${machine.id}-${product.id}`] ||
                                Number(addQuantityByMachineProduct[`${machine.id}-${product.id}`]) > Number(product.quantity || 0)
                              }
                            >
                              Add Quantity
                            </button>
                          </div>
                          <div className="d-flex flex-wrap align-items-center gap-2">
                            <input
                              type="number"
                              className="form-control form-control-sm"
                              style={{ maxWidth: '120px' }}
                              min="1"
                              max={product.machine_quantity || 0}
                              step="1"
                              placeholder="Sell qty"
                              value={deleteQuantityByMachineProduct[`${machine.id}-${product.id}`] || ''}
                              onChange={(e) =>
                                setDeleteQuantityByMachineProduct((prev) => ({
                                  ...prev,
                                  [`${machine.id}-${product.id}`]: e.target.value,
                                }))
                              }
                            />
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => deleteMachineProductQuantity(machine.id, product.id)}
                              disabled={!deleteQuantityByMachineProduct[`${machine.id}-${product.id}`]}
                            >
                              Sell
                            </button>
                          </div>
                          <div className="d-flex flex-wrap align-items-center gap-2">
                            <input
                              type="number"
                              className="form-control form-control-sm"
                              style={{ maxWidth: '120px' }}
                              min="1"
                              max={product.machine_quantity || 0}
                              step="1"
                              placeholder="Put back qty"
                              value={putBackQuantityByMachineProduct[`${machine.id}-${product.id}`] || ''}
                              onChange={(e) =>
                                setPutBackQuantityByMachineProduct((prev) => ({
                                  ...prev,
                                  [`${machine.id}-${product.id}`]: e.target.value,
                                }))
                              }
                            />
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-primary"
                              onClick={() => putBackMachineProductQuantity(machine.id, product.id)}
                              disabled={!putBackQuantityByMachineProduct[`${machine.id}-${product.id}`]}
                            >
                              Put Back
                            </button>
                          </div>
                          <div>
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-secondary"
                              onClick={() => removeProductFromMachine(machine.id, product.id)}
                            >
                              Put Back All
                            </button>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>

                  <div className="d-flex gap-2 mt-3">
                    <select
                      className="form-select"
                      value={selectedProductByMachine[machine.id] || ''}
                      onChange={(e) =>
                        setSelectedProductByMachine((prev) => ({
                          ...prev,
                          [machine.id]: e.target.value,
                        }))
                      }
                    >
                      <option value="">Select product</option>
                      {products
                        .filter(
                          (product) =>
                            !(machine.products || []).some(
                              (machineProduct) => machineProduct.id === product.id
                            )
                        )
                        .map((product) => (
                          <option key={product.id} value={product.id}>
                            {product.name}
                          </option>
                        ))}
                    </select>

                    <input
                      type="number"
                      className="form-control"
                      style={{ maxWidth: '140px' }}
                      min="1"
                      max={
                        products.find(
                          (product) => String(product.id) === String(selectedProductByMachine[machine.id])
                        )?.quantity || 0
                      }
                      step="1"
                      placeholder="Quantity"
                      value={selectedProductQuantityByMachine[machine.id] || ''}
                      onChange={(e) =>
                        setSelectedProductQuantityByMachine((prev) => ({
                          ...prev,
                          [machine.id]: e.target.value,
                        }))
                      }
                    />

                    <button
                      type="button"
                      className="btn btn-outline-primary"
                      onClick={() => addProductToMachine(machine.id)}
                      disabled={
                        !selectedProductByMachine[machine.id] ||
                        Number(selectedProductQuantityByMachine[machine.id] || 0) <= 0 ||
                        Number(selectedProductQuantityByMachine[machine.id] || 0) >
                          Number(
                            products.find(
                              (product) => String(product.id) === String(selectedProductByMachine[machine.id])
                            )?.quantity || 0
                          )
                      }
                    >
                      Add
                    </button>
                  </div>
                </div>
              </div>
              ))}
            </div>
          )}
        </div>
        </div>
        </section>
        </div>
      </main>
    </ProtectedRoute>
  );
};

export default Home;

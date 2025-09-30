import React, { useEffect, useMemo, useState } from 'react';
import { actionsApi, armoryApi } from '../services/api';
import { AccountIdentifier, ActionResponse, BuyUpgradeRequest, SabotageRequest, SetCreditSavingRequest, SoldierType, TrainingPurchaseRequest, Weapon } from '../types/api';
import Button from './ui/Button';
import Input from './ui/Input';
import Select from './ui/Select';

interface QuickActionsProps {
  accountId: number;
  onClose: () => void;
}

type UpgradeOption = 'siege' | 'fortification' | 'covert' | 'recruiter';

const QuickActions: React.FC<QuickActionsProps> = ({ accountId, onClose }) => {
  const [tab, setTab] = useState<'upgrade' | 'sabotage' | 'training' | 'armory' | 'credit_saving' | 'armory_prefs'>('upgrade');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ActionResponse | null>(null);

  // Upgrade state
  const [upgradeOption, setUpgradeOption] = useState<UpgradeOption>('siege');

  // Sabotage state
  const [weapons, setWeapons] = useState<Weapon[]>([]);
  const [targetUserId, setTargetUserId] = useState<string>('');
  const [spyCount, setSpyCount] = useState<number>(1);
  const [enemyWeaponId, setEnemyWeaponId] = useState<number>(-1);

  // Training state
  const [soldierTypes, setSoldierTypes] = useState<SoldierType[]>([]);
  const [orders, setOrders] = useState<Record<string, number>>({});

  // Credit saving state
  const [creditSavingValue, setCreditSavingValue] = useState<'on' | 'off'>('on');

  // Armory preferences state
  const [weaponPercentages, setWeaponPercentages] = useState<Record<string, number>>({});

  useEffect(() => {
    // Load weapons and soldier types in background
    armoryApi.getWeapons().then(setWeapons).catch(() => {});
    armoryApi.getSoldierTypes().then(setSoldierTypes).catch(() => {});
  }, []);

  // Initialize weapon percentages when weapons load
  useEffect(() => {
    if (weapons.length > 0) {
      const percentages: Record<string, number> = {};
      weapons.forEach(weapon => {
        percentages[weapon.name] = 0;
      });
      setWeaponPercentages(percentages);
    }
  }, [weapons]);

  const actingUser: AccountIdentifier = useMemo(() => ({ id_type: 'id', id: String(accountId) }), [accountId]);

  const submitUpgrade = async () => {
    setLoading(true);
    setResult(null);
    try {
      const req: BuyUpgradeRequest = { acting_user: actingUser, max_retries: 0, upgrade_option: upgradeOption };
      const res = await actionsApi.buyUpgrade(req);
      setResult(res);
    } catch (e: any) {
      setResult({ success: false, error: e?.message || 'Upgrade failed', timestamp: new Date().toISOString() });
    } finally {
      setLoading(false);
    }
  };

  const submitSabotage = async () => {
    if (!targetUserId) return;
    setLoading(true);
    setResult(null);
    try {
      const req: SabotageRequest = {
        acting_user: actingUser,
        max_retries: 0,
        target_id: targetUserId,
        spy_count: spyCount,
        enemy_weapon: enemyWeaponId,
      };
      const res = await actionsApi.sabotage(req);
      setResult(res);
    } catch (e: any) {
      setResult({ success: false, error: e?.message || 'Sabotage failed', timestamp: new Date().toISOString() });
    } finally {
      setLoading(false);
    }
  };

  const submitTraining = async () => {
    setLoading(true);
    setResult(null);
    try {
      const req: TrainingPurchaseRequest = {
        acting_user: actingUser,
        max_retries: 0,
        training_orders: orders,
      };
      const res = await actionsApi.purchaseTraining(req);
      setResult(res);
    } catch (e: any) {
      setResult({ success: false, error: e?.message || 'Training purchase failed', timestamp: new Date().toISOString() });
    } finally {
      setLoading(false);
    }
  };

  const submitCreditSaving = async () => {
    setLoading(true);
    setResult(null);
    try {
      const req: SetCreditSavingRequest = {
        acting_user: actingUser,
        max_retries: 0,
        value: creditSavingValue,
      };
      const res = await actionsApi.setCreditSaving(req);
      setResult(res);
    } catch (e: any) {
      setResult({ success: false, error: e?.message || 'Credit saving update failed', timestamp: new Date().toISOString() });
    } finally {
      setLoading(false);
    }
  };

  const submitArmoryPreferences = async () => {
    setLoading(true);
    setResult(null);
    try {
      const req = {
        weapon_percentages: weaponPercentages,
      };
      const res = await armoryApi.updateArmoryPreferences(accountId, req);
      setResult({ success: true, message: 'Armory preferences updated successfully', timestamp: new Date().toISOString() });
    } catch (e: any) {
      setResult({ success: false, error: e?.message || 'Armory preferences update failed', timestamp: new Date().toISOString() });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-6 text-sm">
          {[
            { id: 'upgrade', label: 'Buy Upgrade' },
            { id: 'sabotage', label: 'Sabotage' },
            { id: 'training', label: 'Purchase Training' },
            { id: 'credit_saving', label: 'Credit Saving' },
            { id: 'armory_prefs', label: 'Armory Prefs' },
          ].map((t: any) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`py-2 px-1 border-b-2 ${tab === t.id ? 'border-primary-500 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {tab === 'upgrade' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Upgrade</label>
            <Select value={upgradeOption} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setUpgradeOption(e.target.value as UpgradeOption)}>
              <option value="siege">Siege</option>
              <option value="fortification">Fortification</option>
              <option value="covert">Covert</option>
              <option value="recruiter">Recruiter</option>
            </Select>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>Close</Button>
            <Button onClick={submitUpgrade} loading={loading}>Buy Upgrade</Button>
          </div>
        </div>
      )}

      {tab === 'sabotage' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Target User ID</label>
            <Input value={targetUserId} onChange={(e) => setTargetUserId(e.target.value)} placeholder="Enter target user id" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Spies to Send</label>
              <Input type="number" min={1} value={spyCount} onChange={(e) => setSpyCount(Number(e.target.value))} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Enemy Weapon</label>
              <Select value={enemyWeaponId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setEnemyWeaponId(Number(e.target.value))}>
                <option value={-1}>Auto-select</option>
                {weapons.map(w => (
                  <option key={w.id} value={w.id}>{w.display_name}</option>
                ))}
              </Select>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>Close</Button>
            <Button onClick={submitSabotage} loading={loading}>Sabotage</Button>
          </div>
        </div>
      )}

      {tab === 'training' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {soldierTypes.map(st => (
              <div key={st.id} className="bg-gray-50 p-3 rounded border">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{st.display_name}</div>
                    <div className="text-xs text-gray-500">{st.name}</div>
                  </div>
                  <Input
                    type="number"
                    min={0}
                    value={orders[st.name] || 0}
                    onChange={(e) => setOrders({ ...orders, [st.name]: Math.max(0, Number(e.target.value)) })}
                    className="w-28"
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>Close</Button>
            <Button onClick={submitTraining} loading={loading}>Purchase Training</Button>
          </div>
        </div>
      )}

      {tab === 'credit_saving' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Credit Saving</label>
            <Select value={creditSavingValue} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setCreditSavingValue(e.target.value as 'on' | 'off')}>
              <option value="on">Enable Credit Saving</option>
              <option value="off">Disable Credit Saving</option>
            </Select>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>Close</Button>
            <Button onClick={submitCreditSaving} loading={loading}>Update Credit Saving</Button>
          </div>
        </div>
      )}

      {tab === 'armory_prefs' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Weapon Percentages</label>
            <div className="text-sm text-gray-600 mb-3">
              Set percentage allocation for each weapon (total: {Object.values(weaponPercentages).reduce((sum, p) => sum + p, 0)}%)
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {weapons.map(weapon => (
                <div key={weapon.id} className="bg-gray-50 p-3 rounded border">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{weapon.display_name}</div>
                      <div className="text-xs text-gray-500">{weapon.name}</div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Input
                        type="number"
                        min={0}
                        max={100}
                        step={0.1}
                        value={weaponPercentages[weapon.name] || 0}
                        onChange={(e) => {
                          const value = Math.max(0, Math.min(100, parseFloat(e.target.value) || 0));
                          setWeaponPercentages({ ...weaponPercentages, [weapon.name]: value });
                        }}
                        className="w-20"
                      />
                      <span className="text-sm text-gray-500">%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>Close</Button>
            <Button onClick={submitArmoryPreferences} loading={loading}>Update Preferences</Button>
          </div>
        </div>
      )}

      {result && (
        <div className={`border rounded p-3 ${result.success ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
          <div className="text-sm font-medium">{result.success ? 'Success' : 'Failed'}</div>
          {result.message && <div className="text-sm text-gray-700 mt-1">{result.message}</div>}
          {result.error && <div className="text-sm text-red-700 mt-1">{result.error}</div>}
        </div>
      )}
    </div>
  );
};

export default QuickActions;



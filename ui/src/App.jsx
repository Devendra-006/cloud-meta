import { useState, useEffect, useCallback } from 'react'
import {
  Activity, Server, Settings, BarChart3, Play, RotateCcw, AlertTriangle,
  TrendingUp, TrendingDown, Clock, DollarSign, Zap, Shield, Target, CheckCircle2,
  XCircle, Info, Cloud, Cpu, HardDrive, Globe, ChevronRight
} from 'lucide-react'
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

const API_BASE = ""

const COLORS = {
  primary: '#3b82f6',
  success: '#22c55e',
  warning: '#eab308',
  danger: '#ef4444',
  purple: '#a855f7',
  cyan: '#06b6d4',
}

const VM_STATES = {
  idle: { color: '#f59e0b', label: 'Idle' },
  active: { color: '#22c55e', label: 'Active' },
  critical: { color: '#ef4444', label: 'Critical' },
  protected: { color: '#a855f7', label: 'Tier-1' },
}

function StatusBadge({ status, children }) {
  const colors = {
    success: 'bg-green-500/20 text-green-400 border-green-500/30',
    warning: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    danger: 'bg-red-500/20 text-red-400 border-red-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  }
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${colors[status] || colors.info}`}>
      {children}
    </span>
  )
}

function MetricCard({ icon: Icon, label, value, subValue, color = COLORS.primary }) {
  return (
    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
      <div className="flex items-center justify-between mb-2">
        <div className="p-2 rounded-lg" style={{ backgroundColor: `${color}20` }}>
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
      </div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      <div className="text-sm text-slate-400">{label}</div>
      {subValue && <div className="text-xs text-slate-500 mt-1">{subValue}</div>}
    </div>
  )
}

function VMCard({ vm, selected, onToggle, disabled, actionType }) {
  const isIdle = vm.cpu_pct < 2 && vm.uptime_hrs > 6
  const isProtected = vm.sla_tier === 1
  const isCritical = vm.cpu_pct > 85
  
  let state = 'active'
  if (isProtected) state = 'protected'
  else if (isCritical) state = 'critical'
  else if (isIdle) state = 'idle'
  
  const stateStyle = VM_STATES[state]

  return (
    <div
      className={`bg-slate-800/50 rounded-lg p-3 cursor-pointer transition-all duration-200 border ${
        selected 
          ? 'ring-2 ring-blue-500 bg-blue-500/10 border-blue-500' 
          : 'border-slate-700 hover:border-slate-600'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      onClick={() => !disabled && onToggle(vm.id)}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-slate-400" />
          <span className="font-mono text-sm font-medium text-white">{vm.id}</span>
        </div>
        <div
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: stateStyle.color }}
        />
      </div>
      
      <div className="grid grid-cols-2 gap-2 text-xs mb-3">
        <div className="flex items-center gap-1 text-slate-400">
          <Cpu className="w-3 h-3" />
          <span>{vm.cpu_pct?.toFixed(1)}%</span>
        </div>
        <div className="flex items-center gap-1 text-slate-400">
          <HardDrive className="w-3 h-3" />
          <span>{vm.mem_pct?.toFixed(1)}%</span>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs font-medium px-2 py-0.5 rounded" style={{ 
          color: stateStyle.color,
          backgroundColor: `${stateStyle.color}20`
        }}>
          {stateStyle.label}
        </span>
        <span className="text-xs text-slate-500">${vm.cost_per_hr?.toFixed(2)}/hr</span>
      </div>

      <div className="mt-2 pt-2 border-t border-slate-700/50 flex items-center gap-2">
        <Globe className="w-3 h-3 text-slate-500" />
        <span className="text-xs text-slate-500">{vm.region}</span>
        <span className="text-xs text-slate-600 ml-auto">{vm.uptime_hrs}h</span>
      </div>
    </div>
  )
}

function SimulationTab({ observation, onAction, disabled, selectedVMs, setSelectedVMs, reasoning, setReasoning }) {
  const [actionType, setActionType] = useState('shutdown')
  const vms = observation?.vms || []

  const handleToggle = (vmId) => {
    if (actionType === 'shutdown' && vms.find(v => v.id === vmId)?.sla_tier === 1) {
      return
    }
    setSelectedVMs(prev => {
      const current = prev[actionType] || []
      if (current.includes(vmId)) {
        return { ...prev, [actionType]: current.filter(id => id !== vmId) }
      }
      return { ...prev, [actionType]: [...current, vmId] }
    })
  }

  const handleAutoGenerate = () => {
    const selected = selectedVMs[actionType] || []
    if (selected.length === 0) {
      setReasoning("Please select VMs first to generate reasoning.")
      return
    }
    const vmList = selected.join(", ")
    if (actionType === "shutdown") {
      setReasoning(`Shutting down ${vmList}. These VMs are idle with CPU usage below 2% and uptime over 6 hours. They are not serving active workloads and can be safely terminated to save costs.`)
    } else if (actionType === "scale_up") {
      setReasoning(`Scaling up ${vmList}. These VMs have high CPU usage above 70% and need more resources for better performance and reliability.`)
    } else {
      setReasoning(`Scaling down ${vmList}. These VMs are over-provisioned with low resource utilization. Right-sizing will reduce costs without affecting performance.`)
    }
  }

  const handleSubmit = () => {
    const action = {
      shutdown: selectedVMs.shutdown || [],
      scale_up: selectedVMs.scale_up || [],
      scale_down: selectedVMs.scale_down || [],
      migrate: [],
      reasoning: reasoning,
    }
    onAction(action)
  }

  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="col-span-2 space-y-4">
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Server className="w-5 h-5 text-blue-400" />
            VM Selection - {actionType === 'shutdown' ? 'Shutdown' : actionType === 'scale_up' ? 'Scale Up' : 'Scale Down'}
            <span className="ml-auto text-sm text-slate-400">
              {selectedVMs[actionType]?.length || 0} selected
            </span>
          </h3>

          <div className="mb-4">
            <div className="flex gap-2">
              {[
                { id: 'shutdown', label: 'Shutdown', icon: XCircle, color: COLORS.danger },
                { id: 'scale_up', label: 'Scale Up', icon: TrendingUp, color: COLORS.success },
                { id: 'scale_down', label: 'Scale Down', icon: TrendingDown, color: COLORS.warning },
              ].map(action => (
                <button
                  key={action.id}
                  onClick={() => setActionType(action.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all border ${
                    actionType === action.id
                      ? 'bg-blue-500/20 text-blue-400 border-blue-500/50'
                      : 'bg-slate-700/50 text-slate-400 border-slate-600 hover:border-slate-500'
                  }`}
                >
                  <action.icon className="w-4 h-4" style={{ color: action.color }} />
                  {action.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 max-h-96 overflow-y-auto">
            {vms.map(vm => (
              <VMCard
                key={vm.id}
                vm={vm}
                selected={selectedVMs[actionType]?.includes(vm.id)}
                onToggle={handleToggle}
                disabled={disabled || (actionType === 'shutdown' && vm.sla_tier === 1)}
                actionType={actionType}
              />
            ))}
          </div>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
          <h3 className="text-sm font-semibold text-slate-300 mb-2">Instructions</h3>
          <p className="text-sm text-slate-400 leading-relaxed">{observation?.instructions || 'No instructions available'}</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            Action Panel
          </h3>

          <div className="mb-4">
            <label className="text-sm text-slate-400 mb-2 block">Selected VMs:</label>
            <div className="flex flex-wrap gap-2 min-h-[32px]">
              {(selectedVMs[actionType] || []).map(vmId => (
                <span key={vmId} className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-sm">
                  {vmId}
                </span>
              ))}
              {(!selectedVMs[actionType] || selectedVMs[actionType].length === 0) && (
                <span className="text-slate-500 text-sm">No VMs selected</span>
              )}
            </div>
          </div>

          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-slate-400">Reasoning</label>
              <button
                onClick={handleAutoGenerate}
                className="text-xs text-blue-400 hover:text-blue-300 underline"
              >
                Auto-generate
              </button>
            </div>
            <textarea
              value={reasoning}
              onChange={(e) => setReasoning(e.target.value)}
              placeholder="Explain why you selected these VMs..."
              className="w-full bg-slate-700/50 border border-slate-600 rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"
              rows={4}
            />
            <p className="text-xs text-slate-500 mt-2">
              Tip: Use keywords like "idle", "CPU", "cost", "SLA" for better scoring
            </p>
          </div>

          <button
            onClick={handleSubmit}
            disabled={disabled || !(selectedVMs[actionType]?.length > 0)}
            className={`w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-all ${
              disabled || !(selectedVMs[actionType]?.length > 0)
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-500 text-white'
            }`}
          >
            <Play className="w-4 h-4" />
            Execute Action
          </button>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Quick Stats</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Budget:</span>
              <span className="text-white font-medium">${observation?.budget_remaining?.toFixed(2) || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Fleet Size:</span>
              <span className="text-white font-medium">{vms.length} VMs</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Step:</span>
              <span className="text-white font-medium">{observation?.step_number || 0}/{observation?.max_steps || 1}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function DashboardTab({ observation, stepHistory, rewardResult, onReset }) {
  const vms = observation?.vms || []
  const totalCost = vms.reduce((sum, vm) => sum + (vm.cost_per_hr || 0), 0)
  const avgCpu = vms.length ? vms.reduce((sum, vm) => sum + (vm.cpu_pct || 0), 0) / vms.length : 0
  const idleCount = vms.filter(vm => (vm.cpu_pct || 0) < 2 && (vm.uptime_hrs || 0) > 6).length
  const criticalCount = vms.filter(vm => (vm.cpu_pct || 0) > 85).length

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4">
        <MetricCard icon={DollarSign} label="Hourly Cost" value={`$${totalCost.toFixed(2)}`} subValue="Total fleet" color={COLORS.success} />
        <MetricCard icon={Cpu} label="Avg CPU" value={`${avgCpu.toFixed(1)}%`} subValue="Fleet utilization" color={COLORS.primary} />
        <MetricCard icon={Server} label="Idle VMs" value={idleCount} subValue="Candidates for shutdown" color={COLORS.warning} />
        <MetricCard icon={AlertTriangle} label="Critical" value={criticalCount} subValue="Needs attention" color={COLORS.danger} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2">
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Server className="w-5 h-5 text-blue-400" />
              VM Fleet Overview
              <span className="ml-auto text-sm text-slate-400">{vms.length} VMs</span>
            </h3>
            <div className="grid grid-cols-5 gap-3">
              {vms.map(vm => (
                <VMCard key={vm.id} vm={vm} selected={false} onToggle={() => {}} disabled={true} actionType="shutdown" />
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              Alerts
              <span className="ml-auto text-xs text-slate-500">{observation?.active_alerts?.length || 0} issues</span>
            </h3>
            {(observation?.active_alerts || []).length > 0 ? (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {observation.active_alerts.map((alert, idx) => {
                  const severityColors = {
                    critical: 'bg-red-500/20 border-red-500/50',
                    high: 'bg-red-500/15 border-red-500/40',
                    medium: 'bg-yellow-500/15 border-yellow-500/40',
                    low: 'bg-blue-500/10 border-blue-500/30',
                    protected: 'bg-purple-500/20 border-purple-500/50',
                  }
                  const severityText = {
                    critical: 'text-red-400',
                    high: 'text-red-400',
                    medium: 'text-yellow-400',
                    low: 'text-blue-400',
                    protected: 'text-purple-400',
                  }
                  const severityBg = {
                    critical: 'text-red-400',
                    high: 'text-red-400',
                    medium: 'text-yellow-400',
                    low: 'text-blue-400',
                    protected: 'text-purple-400',
                  }
                  
                  return (
                    <div key={idx} className={`rounded-lg p-3 border ${severityColors[alert.severity] || severityColors.low}`}>
                      <div className="flex items-start justify-between mb-1">
                        <span className={`text-sm font-medium ${severityText[alert.severity] || severityText.low}`}>
                          {alert.title || alert.vm_id}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded ${severityBg[alert.severity] || severityBg.low} bg-opacity-20`}>
                          {alert.severity?.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 mb-2">{alert.message}</p>
                      {alert.potential_savings > 0 && (
                        <div className="flex items-center gap-1 text-xs">
                          <DollarSign className="w-3 h-3 text-green-400" />
                          <span className="text-green-400">Save ${alert.potential_savings.toFixed(2)}/hr</span>
                        </div>
                      )}
                      {alert.action && alert.action !== 'none' && (
                        <div className="mt-2 flex gap-2">
                          <span className="text-xs px-2 py-1 bg-slate-700/50 rounded text-slate-300">
                            Action: {alert.action}
                          </span>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                <CheckCircle2 className="w-4 h-4 text-green-400" />
                <span className="text-sm text-green-300">All systems operational</span>
              </div>
            )}
          </div>

          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Task Progress</h3>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-white">
                {observation?.step_number || 0}/{observation?.max_steps || 1}
              </span>
              <div className="flex-1">
                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all"
                    style={{ width: `${((observation?.step_number || 0) / (observation?.max_steps || 1)) * 100}%` }}
                  />
                </div>
              </div>
            </div>
            {rewardResult && (
              <div className="mt-3 pt-3 border-t border-slate-600">
                <div className="flex justify-between">
                  <span className="text-slate-400">Score:</span>
                  <span className="text-lg font-bold text-green-400">{rewardResult.total_score?.toFixed(3) || 0}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            Traffic Forecast
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={(observation?.traffic_forecast || [0.4, 0.45, 0.5, 0.48, 0.42]).map((v, i) => ({ time: `T+${i}h`, load: Math.round(v * 100) }))}>
              <defs>
                <linearGradient id="trafficGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.cyan} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={COLORS.cyan} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} unit="%" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              <Area type="monotone" dataKey="load" stroke={COLORS.cyan} fill="url(#trafficGradient)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-yellow-400" />
            Step History
          </h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {stepHistory.length === 0 ? (
              <p className="text-slate-500 text-sm text-center py-4">No steps taken yet</p>
            ) : (
              stepHistory.map((step, idx) => (
                <div key={idx} className="bg-slate-700/50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-slate-400">Step {idx + 1}</span>
                    <span className="font-mono text-sm font-medium text-white">
                      {step.reward?.toFixed(3) || '0.000'}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 truncate">{step.reasoning || 'No reasoning'}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function AnalyticsTab({ observation, stepHistory, rewardResult }) {
  const historyData = stepHistory.map((step, idx) => ({
    step: idx + 1,
    reward: step.reward || 0,
  }))

  const vms = observation?.vms || []
  const vmCosts = vms.map(vm => ({
    name: vm.id,
    cost: vm.cost_per_hr || 0,
  })).sort((a, b) => b.cost - a.cost)

  const cpuDistribution = [
    { name: 'Idle (<2%)', value: vms.filter(v => (v.cpu_pct || 0) < 2).length, color: COLORS.warning },
    { name: 'Normal (2-70%)', value: vms.filter(v => (v.cpu_pct || 0) >= 2 && (v.cpu_pct || 0) <= 70).length, color: COLORS.success },
    { name: 'High (70-85%)', value: vms.filter(v => (v.cpu_pct || 0) > 70 && (v.cpu_pct || 0) <= 85).length, color: COLORS.warning },
    { name: 'Critical (>85%)', value: vms.filter(v => (v.cpu_pct || 0) > 85).length, color: COLORS.danger },
  ].filter(d => d.value > 0)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-green-400" />
            Reward Progression
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={historyData.length > 0 ? historyData : [{ step: 0, reward: 0 }]}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="step" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" domain={[0, 1]} />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              <Line type="monotone" dataKey="reward" stroke={COLORS.success} strokeWidth={3} dot={{ fill: COLORS.success }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-purple-400" />
            CPU Distribution
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={cpuDistribution.length > 0 ? cpuDistribution : [{ name: 'No Data', value: 1, color: '#666' }]}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={5}
                dataKey="value"
              >
                {cpuDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-yellow-400" />
            VM Cost Analysis
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={vmCosts}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              <Bar dataKey="cost" fill={COLORS.warning} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-purple-400" />
            Reward Breakdown
          </h3>
          {rewardResult ? (
            <div className="space-y-3">
              {[
                { label: 'Cost Savings', value: rewardResult.cost_savings, weight: 0.45, color: COLORS.success },
                { label: 'SLA Compliance', value: rewardResult.sla_compliance, weight: 0.35, color: COLORS.primary },
                { label: 'Action Precision', value: rewardResult.action_precision, weight: 0.15, color: COLORS.purple },
                { label: 'Reasoning', value: rewardResult.reasoning, weight: 0.05, color: COLORS.cyan },
              ].map((comp, idx) => (
                <div key={idx}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-300">{comp.label}</span>
                    <span className="font-mono text-sm font-medium" style={{ color: comp.color }}>
                      {(comp.value * comp.weight).toFixed(3)}
                    </span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${(comp.value || 0) * 100}%`, backgroundColor: comp.color }}
                    />
                  </div>
                </div>
              ))}
              <div className="mt-4 pt-4 border-t border-slate-600">
                <div className="flex items-center justify-between">
                  <span className="text-white font-semibold">Total Score</span>
                  <span className="text-2xl font-bold text-white">{rewardResult.total_score?.toFixed(3) || '0.000'}</span>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-slate-500 text-sm text-center py-8">Execute an action to see breakdown</p>
          )}
        </div>
      </div>
    </div>
  )
}

function SettingsTab() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Info className="w-5 h-5 text-blue-400" />
          About CloudCostEnv
        </h3>
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          CloudCostEnv is an AI training environment for autonomous cloud infrastructure optimization.
          The agent manages VMs, receives real-time telemetry, and takes actions to minimize cost
          while maintaining service reliability.
        </p>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-2xl font-bold text-blue-400">3</div>
            <div className="text-xs text-slate-400">Task Levels</div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-2xl font-bold text-green-400">0.45</div>
            <div className="text-xs text-slate-400">Cost Weight</div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-2xl font-bold text-purple-400">4</div>
            <div className="text-xs text-slate-400">Action Types</div>
          </div>
        </div>
      </div>

      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">How to Play</h3>
        <div className="space-y-3 text-sm text-slate-400">
          <div className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold flex-shrink-0">1</span>
            <p>Select a task (Easy, Medium, Hard) from the dropdown</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold flex-shrink-0">2</span>
            <p>Go to Simulation tab and select VMs for shutdown/scale actions</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold flex-shrink-0">3</span>
            <p>Click "Auto-generate" for reasoning or write your own</p>
          </div>
          <div className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-xs font-bold flex-shrink-0">4</span>
            <p>Click "Execute Action" to submit and see your score</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [taskId, setTaskId] = useState('task1')
  const [observation, setObservation] = useState(null)
  const [rewardResult, setRewardResult] = useState(null)
  const [stepHistory, setStepHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedVMs, setSelectedVMs] = useState({ shutdown: [], scale_up: [], scale_down: [] })
  const [reasoning, setReasoning] = useState('')
  const [episodeId, setEpisodeId] = useState(null)

  const handleReset = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId }),
      })
      if (response.ok) {
        const data = await response.json()
        const obs = data.observation || data
        setObservation(obs)
        setEpisodeId(data.episode_id || null)
        setRewardResult(null)
        setStepHistory([])
        setSelectedVMs({ shutdown: [], scale_up: [], scale_down: [] })
        setReasoning('')
      }
    } catch (error) {
      console.error('Reset error:', error)
    }
    setLoading(false)
  }, [taskId])

  const handleAction = async (action) => {
    setLoading(true)
    try {
      const headers = { 'Content-Type': 'application/json' }
      if (episodeId) {
        headers['X-Episode-ID'] = episodeId
      }
      
      const response = await fetch(`${API_BASE}/step`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ action }),
      })
      
      if (!response.ok) {
        const error = await response.json()
        console.error('Step error:', error)
        setLoading(false)
        return
      }
      
      const data = await response.json()
      
      // Extract observation - it might be nested or direct
      let obs = data.observation
      if (!obs) {
        obs = data  // Fallback to entire response
      }
      
      // Ensure step_number and max_steps are numbers
      const stepNumber = Number(obs.step_number) || 0
      const maxSteps = Number(obs.max_steps) || 1
      
      // Create updated observation with proper values
      const updatedObs = {
        ...obs,
        step_number: stepNumber,
        max_steps: maxSteps,
        reward: data.reward ?? obs.reward,
      }
      
      setObservation(updatedObs)
      
      const result = {
        total_score: data.reward ?? obs.reward ?? 0,
        cost_savings: 0.35,
        sla_compliance: 0.35,
        action_precision: 0.15,
        reasoning: 0.05,
      }
      setRewardResult(result)
      
      setStepHistory(prev => [...prev, {
        step: stepNumber,
        reward: data.reward ?? obs.reward,
        reasoning: action.reasoning,
      }])
      
      setSelectedVMs({ shutdown: [], scale_up: [], scale_down: [] })
      setReasoning('')
    } catch (error) {
      console.error('Action error:', error)
    }
    setLoading(false)
  }

  useEffect(() => {
    handleReset()
  }, [])

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'simulation', label: 'Simulation', icon: Server },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: Settings },
  ]

  return (
    <div className="min-h-screen bg-slate-900">
      <header className="sticky top-0 z-40 bg-slate-800/80 backdrop-blur border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Cloud className="w-8 h-8 text-blue-400" />
                <div>
                  <h1 className="text-xl font-bold text-white">CloudCostEnv</h1>
                  <p className="text-xs text-slate-400">AI Cloud Optimization</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <select
                value={taskId}
                onChange={(e) => {
                  setTaskId(e.target.value)
                }}
                className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              >
                <option value="task1">Task 1 - Easy</option>
                <option value="task2">Task 2 - Medium</option>
                <option value="task3">Task 3 - Hard</option>
              </select>

              <button
                onClick={handleReset}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white hover:border-slate-500 transition-colors disabled:opacity-50"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>

              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${loading ? 'bg-yellow-400 animate-pulse' : 'bg-green-400'}`} />
                <span className="text-xs text-slate-400">
                  {loading ? 'Processing...' : 'Ready'}
                </span>
              </div>
            </div>
          </div>

          <nav className="flex gap-1 mt-4">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {activeTab === 'dashboard' && (
          <DashboardTab observation={observation} stepHistory={stepHistory} rewardResult={rewardResult} onReset={handleReset} />
        )}
        {activeTab === 'simulation' && (
          <SimulationTab 
            observation={observation} 
            onAction={handleAction} 
            disabled={loading || observation?.done}
            selectedVMs={selectedVMs}
            setSelectedVMs={setSelectedVMs}
            reasoning={reasoning}
            setReasoning={setReasoning}
          />
        )}
        {activeTab === 'analytics' && (
          <AnalyticsTab observation={observation} stepHistory={stepHistory} rewardResult={rewardResult} />
        )}
        {activeTab === 'settings' && (
          <SettingsTab />
        )}
      </main>

      {observation?.done && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-2xl p-8 max-w-md w-full mx-4 border border-slate-700">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
              <CheckCircle2 className="w-8 h-8 text-green-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2 text-center">Episode Complete!</h2>
            <div className="text-4xl font-bold text-white mb-4 text-center">
              {(rewardResult?.total_score || 0).toFixed(3)}
            </div>
            <p className="text-slate-400 mb-6 text-center">
              Final score achieved in {stepHistory.length} steps
            </p>
            <button
              onClick={handleReset}
              className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors"
            >
              Start New Episode
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

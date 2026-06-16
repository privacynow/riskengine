import type { Component } from "vue";
import {
  LayoutDashboard,
  FlaskConical,
  ScrollText,
  GitBranch,
  Radio,
  Link2,
  Building2,
  Menu,
  ChevronDown,
  RefreshCw,
  AlertTriangle,
  TrendingUp,
  Zap,
  Plus,
  ArrowRight,
  Layers,
  DollarSign,
  Activity,
} from "@lucide/vue";

export const icons = {
  layoutDashboard: LayoutDashboard,
  flask: FlaskConical,
  scroll: ScrollText,
  gitBranch: GitBranch,
  radio: Radio,
  link: Link2,
  building: Building2,
  menu: Menu,
  chevronDown: ChevronDown,
  refresh: RefreshCw,
  alert: AlertTriangle,
  trend: TrendingUp,
  zap: Zap,
  plus: Plus,
  arrowRight: ArrowRight,
  layers: Layers,
  dollar: DollarSign,
  activity: Activity,
} as const satisfies Record<string, Component>;

export type IconName = keyof typeof icons;

# 前端规范：阿里巴巴 f2e-spec 落地

> 适用范围：`frontend/`（React 18 + TypeScript 5.4 + Vite 5）。
> 权威来源：阿里巴巴前端开发规范 [alibaba/f2e-spec](https://github.com/alibaba/f2e-spec)（`docs/coding/typescript.zh.md`、`docs/coding/react.zh.md`、`docs/coding/common.zh.md`）。
> 落地方式：`eslint-config-ali`（lint）+ `prettier-config-ali`（格式化）。本页只保留适用于本项目的规则摘录。

## 1. React Hooks

- **依赖数组补全**：`useEffect` / `useMemo` / `useCallback` 必须声明所有用到的依赖（`react-hooks/exhaustive-deps`）。若某场景确实不适用，用行注释显式豁免：`// eslint-disable-line react-hooks/exhaustive-deps`。

  ```tsx
  // bad
  const local = {};
  useEffect(() => {
    console.log(local);
  }, []);

  // good
  const local = {};
  useEffect(() => {
    console.log(local);
  }, [local]);
  ```

- **只在最顶层调用 Hooks**：禁止在循环、条件分支、嵌套函数中调用 Hooks。
- **只在 React 函数组件和自定义 Hooks 中调用 Hooks**，不能在普通 JS 函数或 class 组件中调用。
- **自定义 Hooks 命名以 `use` 开头**、小驼峰形式（`useApp`、`useQuotes`）。

## 2. 命名

- **组件引用名使用 PascalCase**（大驼峰）：`import PriceCard from './PriceCard';`
- **组件文件名与导出组件名一致**：`PriceCard.tsx` 导出 `PriceCard`。
- **组件实例 / 引用使用小驼峰**：`const priceCard = <PriceCard />;`
- **props 回调以 `on` 前缀**：`onRead`、`onSelect`、`onRefresh`。
- **布尔 props 以 `is` / `has` 前缀**：`isLoading`、`hasError`。
- props 用小驼峰命名（`userName`、`phoneNumber`，不要 `phone_number` 或 `UserName`）。

## 3. 类型

- **禁止 `any`**：优先用精确类型；确需宽松时用 `unknown` 并做收窄。
- **props 用 `interface` 显式定义**（优先 interface 而非 type 描述对象形状），成员分隔符统一 `;`：

  ```tsx
  interface PriceCardProps {
    symbol: string;
    isFalling: boolean;
    onRead?: (id: string) => void;
  }
  ```

- **纯类型导入用 `import type`**，与值导入分离：

  ```tsx
  import type { Quote, Position, NewsItem } from '../types';
  import { useApp } from '../store';
  ```

## 4. 导入

- **分组排序**：外部包（react / zustand / echarts）在前，内部相对导入在后；组内按字母序（eslint import 规则检查）。
- **`import type` 分离**：纯类型导入独立一行。
- 类型注解间距：冒号前无空格、冒号后一个空格；箭头函数前后各一个空格。

## 5. Prettier 选项

来自 `prettier-config-ali`（通过 `frontend/.prettierrc` 引用），本项目生效值：

| 选项 | 值 |
| --- | --- |
| `printWidth` | 100 |
| `tabWidth` | 2 |
| `singleQuote` | true |
| `semi` | true |
| `trailingComma` | all |
| 换行 | LF（`.editorconfig` 保证） |

## 6. JSX

- **无子元素的标签写成自闭合**：`<Foo bar="baz" />`；自闭合标签斜线前一个空格。
- **JSX 缩进 2 空格**（阿里通用规约）；多行 JSX 用小括号包裹。
- **列表渲染 `key` 唯一且稳定**：不要用数组索引作 `key`（`react/no-array-index-key`）；优先用数据自带的稳定 id。
- JSX 属性用双引号，JS 字符串用单引号。
- 不要在 JSX 属性里用 `.bind()` 或内联过重的回调；状态更新优先函数式（如 zustand 的 `set(state => ...)`）。

## 常用命令

```bash
cd frontend
npm run lint          # eslint .
npm run lint:fix      # eslint . --fix
npm run format        # prettier --write .
npm run format:check  # prettier --check .
npm run build         # tsc -b && vite build
```

<!-- SOURCE pdf-186-b000 -->
<div id="pdf-186-b000" hidden></div>
# 危险信号汇总 {#red-flags}

<!-- SOURCE pdf-186-b001 -->
<div id="pdf-186-b001" hidden></div>
以下列出本书讨论的若干主要危险信号。系统中只要出现这些症状中的任何一种，就说明设计可能存在问题：

<!-- SOURCE pdf-186-b002 -->
<div id="pdf-186-b002" hidden></div>
## 浅模块 {#red-flags-section-01}

类或方法的接口，与其实现相比并没有简单多少（见原书第 25、110 页）。

<!-- SOURCE pdf-186-b003 -->
<div id="pdf-186-b003" hidden></div>
## 信息泄漏 {#red-flags-section-02}

同一个设计决策体现在多个模块中（见原书第 31 页）。

<!-- SOURCE pdf-186-b004 -->
<div id="pdf-186-b004" hidden></div>
## 按时间顺序分解 {#red-flags-section-03}

代码结构依据操作的执行顺序组织，未按信息隐藏的原则组织（见原书第 32 页）。

<!-- SOURCE pdf-186-b005 -->
<div id="pdf-186-b005" hidden></div>
## 暴露过多细节 {#red-flags-section-04}

API 让调用者为了使用常见功能，不得不了解很少用到的功能（见原书第 36 页）。

<!-- SOURCE pdf-186-b006 -->
<div id="pdf-186-b006" hidden></div>
## 透传方法 {#red-flags-section-05}

一个方法几乎什么也不做，只把参数传给签名相似的另一个方法（见原书第 46 页）。

<!-- SOURCE pdf-186-b007 -->
<div id="pdf-186-b007" hidden></div>
## 重复 {#red-flags-section-06}

一段具有实质功能的代码反复出现（见原书第 62 页）。

<!-- SOURCE pdf-186-b008 -->
<div id="pdf-186-b008" hidden></div>
## 专用与通用代码混杂 {#red-flags-section-07}

专用代码没有与通用代码清楚分开（见原书第 65 页）。

<!-- SOURCE pdf-186-b009 -->
<div id="pdf-186-b009" hidden></div>
## 相互纠缠的方法 {#red-flags-section-08}

两个方法之间依赖太多，理解其中一个的实现时，很难不去理解另一个的实现（见原书第 72 页）。

<!-- SOURCE pdf-186-b010 -->
<div id="pdf-186-b010" hidden></div>
## 注释重复代码 {#red-flags-section-09}

注释中的全部信息，都能从它旁边的代码中直接看出来（见原书第 104 页）。

<!-- SOURCE pdf-186-b011 -->
<div id="pdf-186-b011" hidden></div>
## 实现文档侵入接口说明 {#red-flags-section-10}

接口注释描述了使用者无须了解的实现细节（见原书第 114 页）。

<!-- SOURCE pdf-186-b012 -->
<div id="pdf-186-b012" hidden></div>
## 名称含糊 {#red-flags-section-11}

变量或方法的名称不够精确，传达不了多少有用信息（见原书第 123 页）。

<!-- SOURCE pdf-187-b000 -->
<div id="pdf-187-b000" hidden></div>
## 难以命名 {#red-flags-section-12}

很难为某个实体找到精确、直观的名称（见原书第 125 页）。

<!-- SOURCE pdf-187-b001 -->
<div id="pdf-187-b001" hidden></div>
## 难以描述 {#red-flags-section-13}

为了完整说明某个变量或方法，不得不写很长的文档（见原书第 131 页）。

<!-- SOURCE pdf-187-b002 -->
<div id="pdf-187-b002" hidden></div>
## 代码含义不清楚 {#red-flags-section-14}

一段代码的行为或含义不容易理解（见原书第 148 页）。

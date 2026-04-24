# Claude vs Gemini 判定相違レビュー

検証: 54カテゴリ / 一致 24 / 相違 16 / エラー 14

## 相違一覧

### ヒト成長ホルモン剤
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: ヒト成長ホルモン剤は、告示第十第一号に「保険医が投与することができる注射薬」として明記されており、自己注射が一般的に行われる薬剤であるため、院外処方箋での処方が可能です。
- **告示原文**: 
  > 第十　厚生労働大臣が定める注射薬等
  > 一　療担規則第二十条第二号ト及び療担基準第二十条第三号トの厚生労働大臣が定める保険医が投与することができる注射薬
  > インスリン製剤、ヒト成長ホルモン剤、遺伝子組換え活性型血液凝固第Ⅶ因子製剤、乾燥濃縮人血液凝固第Ⅹ因子加活性化第Ⅶ因子製剤、乾燥人血液凝固第Ⅷ因子製剤、遺伝子組換え型血液凝固第Ⅷ因子製剤、乾燥人血液凝固第Ⅸ因子製剤、遺伝子組換え型血液凝固第Ⅸ因子製剤、活性化プロトロンビン複合体、乾燥

### 遺伝子組換え活性型血液凝固第Ⅶ因子製剤
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 告示第十第一号に「遺伝子組換え活性型血液凝固第Ⅶ因子製剤」が保険医が投与できる注射薬として明確に列挙されており、院外処方を制限する条件は付されていないため、院外処方箋での処方が可能です。
- **告示原文**: 
  > 第十　厚生労働大臣が定める注射薬等
  > 一　療担規則第二十条第二号ト及び療担基準第二十条第三号トの厚生労働大臣が定める保険医が投与することができる注射薬
  > インスリン製剤、ヒト成長ホルモン剤、遺伝子組換え活性型血液凝固第Ⅶ因子製剤、乾燥濃縮人血液凝固第Ⅹ因子加活性化第Ⅶ因子製剤、乾燥人血液凝固第Ⅷ因子製剤、遺伝子組換え型血液凝固第Ⅷ因子製剤、乾燥人血液凝固第Ⅸ因子製剤、遺伝子組換え型血液凝固第Ⅸ因子製剤、活性化プロトロンビン複合体、乾燥人血液凝固因子抗体迂う回活性複合体、性腺

### 乾燥人血液凝固第Ⅷ因子製剤
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 乾燥人血液凝固第Ⅷ因子製剤は、厚生労働省告示第107号第十第一号において「保険医が投与することができる注射薬」として具体的に列挙されています。この告示は、在宅医療等で医師が患家で投与する、または患者が自己注射する注射薬の院外処方を認めるものであり、本製剤には特別な条件が付されていないため、無条件で院外処方可能です。
- **告示原文**: 
  > 一　療担規則第二十条第二号ト及び療担基準第二十条第三条トの厚生労働大臣が定める保険医が投与することができる注射薬
  > インスリン製剤、ヒト成長ホルモン剤、遺伝子組換え活性型血液凝固第Ⅶ因子製剤、乾燥濃縮人血液凝固第Ⅹ因子加活性化第Ⅶ因子製剤、乾燥人血液凝固第Ⅷ因子製剤、遺伝子組換え型血液凝固第Ⅷ因子製剤、乾燥人血液凝固第Ⅸ因子製剤、遺伝子組換え型血液凝固第Ⅸ因子製剤、活性化プロトロンビン複合体、乾燥人血液凝固因子抗体迂う回活性複合体、性腺刺激ホルモン放出ホルモン剤、性腺刺激ホルモン製剤、ゴナドトロピン放出ホルモン

### 遺伝子組換え型血液凝固第Ⅷ因子製剤
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 告示第十第一号に「遺伝子組換え型血液凝固第Ⅷ因子製剤」が保険医が投与できる注射薬として明記されており、自己注射が一般的な薬剤であるため、院外処方箋による処方が無条件で可能と判断される。
- **告示原文**: 
  > 十条第二号ト及び療担基準第二十条第三号トの厚生労働大臣が定める保険医が投与することができる注射薬
  > インスリン製剤、ヒト成長ホルモン剤、遺伝子組換え活性型血液凝固第Ⅶ因子製剤、乾燥濃縮人血液凝固第Ⅹ因子加活性化第Ⅶ因子製剤、乾燥人血液凝固第Ⅷ因子製剤、遺伝子組換え型血液凝固第Ⅷ因子製剤、乾燥人血液凝固第Ⅸ因子製剤、遺伝子組換え型血液凝固第Ⅸ因子製剤、活性化プロトロンビン複合体、乾燥人血液凝固因子抗体迂う回活性複合体、性腺刺激ホルモン放出ホルモン剤、性腺刺激ホルモン製剤、ゴナドトロピン放出ホルモン誘導体、ソマトスタチンアナログ、顆か

### 遺伝子組換え型血液凝固第Ⅸ因子製剤
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 告示第十第一号に「遺伝子組換え型血液凝固第Ⅸ因子製剤」が明記されており、院外処方を制限する条件は付されていません。血友病治療薬として在宅での自己注射が一般的であり、在宅自己注射指導管理料の対象薬剤として院外処方箋による交付が想定されます。
- **告示原文**: 
  > 険医が投与することができる注射薬 インスリン製剤、ヒト成長ホルモン剤、遺伝子組換え活性型血液凝固第Ⅶ因子製剤、乾燥濃縮人血液凝固第Ⅹ因子加活性化第Ⅶ因子製剤、乾燥人血液凝固第Ⅷ因子製剤、遺伝子組換え型血液凝固第Ⅷ因子製剤、乾燥人血液凝固第Ⅸ因子製剤、遺伝子組換え型血液凝固第Ⅸ因子製剤、活性化プロトロンビン複合体、乾燥人血液凝固因子抗体迂う回活性複合体、性腺刺激ホルモン放出ホルモン剤、性腺刺激ホルモン製剤、ゴナドトロピン放出ホルモン誘導体、ソマトスタチンアナログ、顆か粒球コロニー形成刺激因子製剤、自己連続携行式腹膜灌かん流用灌かん

### 活性化プロトロンビン複合体
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 告示第十第一号に「活性化プロトロンビン複合体」が明確に列挙されており、在宅医療において保険医が投与できる注射薬として指定されています。特別な条件も付されていないため、院外処方箋での処方が可能です。
- **告示原文**: 
  > ンスリン製剤、ヒト成長ホルモン剤、遺伝子組換え活性型血液凝固第Ⅶ因子製剤、乾燥濃縮人血液凝固第Ⅹ因子加活性化第Ⅶ因子製剤、乾燥人血液凝固第Ⅷ因子製剤、遺伝子組換え型血液凝固第Ⅷ因子製剤、乾燥人血液凝固第Ⅸ因子製剤、遺伝子組換え型血液凝固第Ⅸ因子製剤、活性化プロトロンビン複合体、乾燥人血液凝固因子抗体迂う回活性複合体、性腺刺激ホルモン放出ホルモン剤、性腺刺激ホルモン製剤、ゴナドトロピン放出ホルモン誘導体、ソマトスタチンアナログ、顆か粒球コロニー形成刺激因子製剤、自己連続携行式腹膜灌かん流用灌かん流液、在宅中心静脈栄養法用輸

### 性腺刺激ホルモン放出ホルモン剤
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 告示第十第一号に「性腺刺激ホルモン放出ホルモン剤」が明確に列挙されており、在宅医療において保険医が投与できる注射薬として、院外処方箋での交付に特段の条件が示されていないため、無条件で院外処方可能と判断される。
- **告示原文**: 
  > 製剤、乾燥濃縮人血液凝固第Ⅹ因子加活性化第Ⅶ因子製剤、乾燥人血液凝固第Ⅷ因子製剤、遺伝子組換え型血液凝固第Ⅷ因子製剤、乾燥人血液凝固第Ⅸ因子製剤、遺伝子組換え型血液凝固第Ⅸ因子製剤、活性化プロトロンビン複合体、乾燥人血液凝固因子抗体迂う回活性複合体、性腺刺激ホルモン放出ホルモン剤、性腺刺激ホルモン製剤、ゴナドトロピン放出ホルモン誘導体、ソマトスタチンアナログ、顆か粒球コロニー形成刺激因子製剤、自己連続携行式腹膜灌かん流用灌かん流液、在宅中心静脈栄養法用輸液、インターフェロンアルファ製剤、インターフェロンベータ製剤、ブプレノル

### ゴナドトロピン放出ホルモン誘導体
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 「療担規則及び薬担規則並びに療担基準に基づき厚生労働大臣が定める掲示事項等」の第十第一号に「ゴナドトロピン放出ホルモン誘導体」が明確に列挙されており、かつ告示上、院外処方に関する特段の条件が付されていないため、無条件で院外処方箋による処方が可能です。
- **告示原文**: 
  > 性腺刺激ホルモン放出ホルモン剤、性腺刺激ホルモン製剤、ゴナドトロピン放出ホルモン誘導体、ソマトスタチンアナログ、顆か粒球コロニー形成刺激因子製剤、自己連続携行式腹膜灌かん流用灌かん流液、在宅中心静脈栄養法用輸液、インターフェロンアルファ製剤、インターフェロンベータ製剤、ブプレノルフィン製剤、抗悪性腫瘍剤、グルカゴン製剤、グルカゴン様ペ

### ソマトスタチンアナログ
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 「療担規則及び薬担規則並びに療担基準に基づき厚生労働大臣が定める掲示事項等」第十第一号に「ソマトスタチンアナログ」が明確に列挙されており、投与に関する特段の条件が記載されていないため、院外処方箋での処方が可能です。
- **告示原文**: 
  > 組換え型血液凝固第Ⅷ因子製剤、乾燥人血液凝固第Ⅸ因子製剤、遺伝子組換え型血液凝固第Ⅸ因子製剤、活性化プロトロンビン複合体、乾燥人血液凝固因子抗体迂う回活性複合体、性腺刺激ホルモン放出ホルモン剤、性腺刺激ホルモン製剤、ゴナドトロピン放出ホルモン誘導体、ソマトスタチンアナログ、顆か粒球コロニー形成刺激因子製剤、自己連続携行式腹膜灌かん流用灌かん流液、在宅中心静脈栄養法用輸液、インターフェロンアルファ製剤、インターフェロンベータ製剤、ブプレノルフィン製剤、抗悪性腫瘍剤、グルカゴン製剤、グルカゴン様ペプチド―1受容体アゴニス

### 顆か粒球コロニー形成刺激因子製剤
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 「顆粒球コロニー形成刺激因子製剤」は、告示第十第一号に保険医が在宅医療において患家で投与できる注射薬として明記されており、特別な条件や制限の記載がないため、院外処方箋による処方も可能です。
- **告示原文**: 
  > 製剤、乾燥人血液凝固第Ⅸ因子製剤、遺伝子組換え型血液凝固第Ⅸ因子製剤、活性化プロトロンビン複合体、乾燥人血液凝固因子抗体迂う回活性複合体、性腺刺激ホルモン放出ホルモン剤、性腺刺激ホルモン製剤、ゴナドトロピン放出ホルモン誘導体、ソマトスタチンアナログ、顆か粒球コロニー形成刺激因子製剤、自己連続携行式腹膜灌かん流用灌かん流液、在宅中心静脈栄養法用輸液、インターフェロンアルファ製剤、インターフェロンベータ製剤、ブプレノルフィン製剤、抗悪性腫瘍剤、グルカゴン製剤、グルカゴン様ペプチド―1受容体アゴニスト、ヒトソマトメジンC製剤、人工腎

### 自己連続携行式腹膜灌かん流用灌かん流液
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 告示第十第一号に「自己連続携行式腹膜灌かん流用灌かん流液」が明確に列挙されており、在宅医療における自己管理を前提とした薬剤であるため、院外処方箋による処方が無条件で可能です。
- **告示原文**: 
  > 顆か粒球コロニー形成刺激因子製剤、自己連続携行式腹膜灌かん流用灌かん流液、在宅中心静脈栄養法用輸液、インターフェロンアルファ製剤、インターフェロンベータ製剤、ブプレノルフィン製剤、抗悪性腫瘍剤、グルカゴン製剤、グルカゴン様ペプチド―1受容体アゴニスト、ヒトソマトメジンC製剤、人工腎臓用透析液(在宅血液透析を行っている患者

### 抗悪性腫瘍剤
- **Claude判定**: `△`
- **Gemini判定**: `○`
- **Geminiの理由**: 告示第十第一号に「抗悪性腫瘍剤」が保険医が投与することができる注射薬として具体的に列挙されており、院外処方に関する特段の制限は記載されていないため。
- **告示原文**: 
  > ルモン製剤、ゴナドトロピン放出ホルモン誘導体、ソマトスタチンアナログ、顆か粒球コロニー形成刺激因子製剤、自己連続携行式腹膜灌かん流用灌かん流液、在宅中心静脈栄養法用輸液、インターフェロンアルファ製剤、インターフェロンベータ製剤、ブプレノルフィン製剤、抗悪性腫瘍剤、グルカゴン製剤、グルカゴン様ペプチド―1受容体アゴニスト、ヒトソマトメジンC製剤

### グルカゴン様ペプチド―1受容体アゴニスト
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 告示第十第一号に「グルカゴン様ペプチド―1受容体アゴニスト」が保険医が投与することができる注射薬として明記されており、院外処方に関する特段の制限がないため。
- **告示原文**: 
  > ホルモン誘導体、ソマトスタチンアナログ、顆か粒球コロニー形成刺激因子製剤、自己連続携行式腹膜灌かん流用灌かん流液、在宅中心静脈栄養法用輸液、インターフェロンアルファ製剤、インターフェロンベータ製剤、ブプレノルフィン製剤、抗悪性腫瘍剤、グルカゴン製剤、グルカゴン様ペプチド―1受容体アゴニスト、ヒトソマトメジンC製剤、人工腎臓用透析液(在宅血液透析を行っている患者(以下「在宅血液透析患者」という。)に対して使用する場合に限る。)

### ヒトソマトメジンC製剤
- **Claude判定**: `?`
- **Gemini判定**: `×`
- **Geminiの理由**: 告示第十第一号は「保険医が投与することができる注射薬」を列挙しており、ヒトソマトメジンC製剤はこれに該当する。しかし、院外処方に関する明示的な記載がなく、原則として院内処方が想定されるため、院外処方は不可と判断される。
- **告示原文**: 
  > ヒトソマトメジンC製剤、人工腎臓用透析液(在宅血液透析を行っている患者(以下「在宅血液透析患者」という。)に対して使用する場合に限る。)、血液凝固阻止剤(在宅血液透析患者に対して使用する場合に限る。)、生理食塩水(在宅血液透析患者に対して使用する場合及び本号に掲げる注射薬

### プロスタグランジンI2製剤
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 告示第十第一号に「プロスタグランジンI2製剤」が保険医が投与することができる注射薬として明記されており、院外処方に関する特段の制限がないため、無条件で院外処方可能です。
- **告示原文**: 
  > 生理食塩水(在宅血液透析患者に対して使用する場合及び本号に掲げる注射薬を投与するに当たりその溶解又は希釈に用いる場合に限る。)、プロスタグランジンI2製剤、モルヒネ塩酸塩製剤、エタネルセプト製剤、注射用水(本号に掲げる注射薬を投与するに当たりその溶解又は希釈に用いる場合に限る。)

### デキサメタゾンメタスルホ安息香酸エステルナトリウム製剤
- **Claude判定**: `?`
- **Gemini判定**: `○`
- **Geminiの理由**: 告示第十第一号に「デキサメタゾンメタスルホ安息香酸エステルナトリウム製剤」が明記されており、保険医が投与できる注射薬として列挙されているため、院外処方可能です。特に条件の記載はありません。
- **告示原文**: 
  > ベタメタゾンリン酸エステルナトリウム製剤、デキサメタゾンリン酸エステルナトリウム製剤、デキサメタゾンメタスルホ安息香酸エステルナトリウム製剤、プロトンポンプ阻害剤、H2遮断剤、カルバゾクロムスルホン酸ナトリウム製剤、トラネキサム酸製剤、フルルビプロフェンアキセチル製剤、メトクロプラミド製剤、プロクロルペラジン製剤、ブチルスコポラミン臭化物製剤、グリチルリチン酸モノアンモニウム・グリシン・

## エラー

- **プロトンポンプ阻害剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **H2遮断剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **カルバゾクロムスルホン酸ナトリウム製剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **トラネキサム酸製剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **フルルビプロフェンアキセチル製剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **メトクロプラミド製剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **プロクロルペラジン製剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **ブチルスコポラミン臭化物製剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **グリチルリチン酸モノアンモニウム・グリシン・L―システイン塩酸塩配合剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **アダリムマブ製剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **エリスロポエチン**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **ダルベポエチン**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **ヘパリンカルシウム製剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
- **オキシコドン塩酸塩製剤**: Gemini error (rc=4): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rat
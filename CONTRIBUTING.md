# 小组协作

## 获取项目

成员接受仓库所有者在 Settings → Collaborators 发出的邀请后克隆仓库。

~~~bash
git clone https://github.com/liqiankun12/travel-itinerary-planner.git
cd travel-itinerary-planner
~~~

## 开始任务

~~~bash
git switch main
git pull --ff-only
git switch -c feat/trip-create
~~~

完成一个可核查的改动后，添加该任务文件，再提交和推送。

~~~bash
git add <本次修改的文件>
git commit -m "feat: 创建旅行表单"
git push -u origin feat/trip-create
~~~

在 GitHub 发起 Pull Request，由一名队友评审并确认验收后合并。继续更新同一分支使用 git push。main 保留团队检查过的成果。

GitHub 展示已推送提交。建议小功能完成或当天收工前更新。成员在自己电脑配置本人 Git 姓名和邮箱。

## 更新资料

需求按版本保存。变更记录原因、影响和测试。站会按日期建文件，填写真实进展。
参考资料保存来源链接和说明。提交时关联任务编号，PR 如实填写验证结果。

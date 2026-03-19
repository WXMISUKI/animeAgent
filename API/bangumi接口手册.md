Bangumi API
 2026-02-22 
OAS 3.0
./dist.json
你可以在 https://next.bgm.tv/demo/access-token 生成一个 Access Token

关于 User Agent
如果你在使用中遇到了问题，请优先使用 GitHub issue 提交问题。在 bangumi 小组发帖可能无法得到及时反馈。

Bangumi API - Website
Servers

https://api.bgm.tv

Authorize
条目


GET
/calendar
每日放送


POST
/v0/search/subjects
条目搜索


GET
/v0/subjects
浏览条目



GET
/v0/subjects/{subject_id}
获取条目



GET
/v0/subjects/{subject_id}/image
Get Subject Image



GET
/v0/subjects/{subject_id}/persons
Get Subject Persons



GET
/v0/subjects/{subject_id}/characters
Get Subject Characters



GET
/v0/subjects/{subject_id}/subjects
Get Subject Relations


章节


GET
/v0/episodes
Get Episodes



GET
/v0/episodes/{episode_id}
Get Episode


角色


POST
/v0/search/characters
角色搜索


GET
/v0/characters/{character_id}
Get Character Detail


GET
/v0/characters/{character_id}/image
Get Character Image



GET
/v0/characters/{character_id}/subjects
get character related subjects


GET
/v0/characters/{character_id}/persons
get character related persons


POST
/v0/characters/{character_id}/collect
Collect character for current user



DELETE
/v0/characters/{character_id}/collect
Uncollect character for current user


人物


POST
/v0/search/persons
人物搜索


GET
/v0/persons/{person_id}
Get Person


GET
/v0/persons/{person_id}/image
Get Person Image



GET
/v0/persons/{person_id}/subjects
get person related subjects


GET
/v0/persons/{person_id}/characters
get person related characters


POST
/v0/persons/{person_id}/collect
Collect person for current user



DELETE
/v0/persons/{person_id}/collect
Uncollect person for current user


用户


GET
/v0/users/{username}
Get User by name


GET
/v0/users/{username}/avatar
Get User Avatar by name


GET
/v0/me
Get User


收藏


GET
/v0/users/{username}/collections
获取用户收藏



GET
/v0/users/{username}/collections/{subject_id}
获取用户单个条目收藏



POST
/v0/users/-/collections/{subject_id}
新增或修改用户单个条目收藏



PATCH
/v0/users/-/collections/{subject_id}
修改用户单个收藏



GET
/v0/users/-/collections/{subject_id}/episodes
章节收藏信息



PATCH
/v0/users/-/collections/{subject_id}/episodes
章节收藏信息



GET
/v0/users/-/collections/-/episodes/{episode_id}
章节收藏信息



PUT
/v0/users/-/collections/-/episodes/{episode_id}
更新章节收藏信息



GET
/v0/users/{username}/collections/-/characters
获取用户角色收藏列表


GET
/v0/users/{username}/collections/-/characters/{character_id}
获取用户单个角色收藏信息


GET
/v0/users/{username}/collections/-/persons
获取用户人物收藏列表


GET
/v0/users/{username}/collections/-/persons/{person_id}
获取用户单个人物收藏信息

编辑历史


GET
/v0/revisions/persons
Get Person Revisions


GET
/v0/revisions/persons/{revision_id}
Get Person Revision


GET
/v0/revisions/characters
Get Character Revisions


GET
/v0/revisions/characters/{revision_id}
Get Character Revision


GET
/v0/revisions/subjects
Get Subject Revisions


GET
/v0/revisions/subjects/{revision_id}
Get Subject Revision


GET
/v0/revisions/episodes
Get Episode Revisions


GET
/v0/revisions/episodes/{revision_id}
Get Episode Revision

目录


POST
/v0/indices
Create a new index



GET
/v0/indices/{index_id}
Get Index By ID



PUT
/v0/indices/{index_id}
Edit index's information



GET
/v0/indices/{index_id}/subjects
Get Index Subjects



POST
/v0/indices/{index_id}/subjects
Add a subject to Index



PUT
/v0/indices/{index_id}/subjects/{subject_id}
Edit subject information in a index



DELETE
/v0/indices/{index_id}/subjects/{subject_id}
Delete a subject from a Index



POST
/v0/indices/{index_id}/collect
Collect index for current user



DELETE
/v0/indices/{index_id}/collect
Uncollect index for current user



Schemas
Legacy_SubjectTypeinteger
example: 2
条目类型
1 = book
2 = anime
3 = music
4 = game
6 = real

Enum:
Array [ 5 ]
Legacy_SubjectSmall{
id	[...]
url	[...]
type	SubjectType[...]
name	[...]
name_cn	[...]
summary	[...]
air_date	[...]
air_weekday	[...]
images	{...}
eps	[...]
eps_count	[...]
rating	{...}
rank	[...]
collection	{...}
}
Legacy_SubjectMedium{
id	[...]
url	[...]
type	SubjectType[...]
name	[...]
name_cn	[...]
summary	[...]
air_date	[...]
air_weekday	[...]
images	{...}
eps	[...]
eps_count	[...]
rating	{...}
rank	[...]
collection	{...}
crt	[...]
staff	[...]
}
Legacy_SubjectLarge{
id	[...]
url	[...]
type	SubjectType[...]
name	[...]
name_cn	[...]
summary	[...]
air_date	[...]
air_weekday	[...]
images	{...}
eps	[...]
eps_count	[...]
rating	{...}
rank	[...]
collection	{...}
crt	[...]
staff	[...]
topic	[...]
blog	[...]
}
Legacy_EpisodeTypeinteger
example: 0
章节类型
0 = 本篇
1 = 特别篇
2 = OP
3 = ED
4 = 预告/宣传/广告
5 = MAD
6 = 其他

Enum:
Array [ 7 ]
Legacy_Episode{
description:	
章节信息

id	[...]
url	[...]
type	Legacy_EpisodeType[...]
sort	[...]
name	[...]
name_cn	[...]
duration	[...]
airdate	[...]
comment	[...]
desc	[...]
status	[...]
}
Legacy_Topic{
description:	
讨论版

id	[...]
url	[...]
title	[...]
main_id	[...]
timestamp	[...]
lastpost	[...]
replies	[...]
user	Legacy_User{...}
}
Legacy_Blog{
description:	
日志

id	[...]
url	[...]
title	[...]
summary	[...]
image	[...]
replies	[...]
timestamp	[...]
dateline	[...]
user	Legacy_User{...}
}
Legacy_User{
description:	
用户信息

id	[...]
url	[...]
username	[...]
nickname	[...]
avatar	{...}
sign	[...]
usergroup	Legacy_UserGroup[...]
}
Legacy_UserGroupinteger
example: 11
用户组
1 = 管理员
2 = Bangumi 管理猿
3 = 天窗管理猿
4 = 禁言用户
5 = 禁止访问用户
8 = 人物管理猿
9 = 维基条目管理猿
10 = 用户
11 = 维基人

Enum:
Array [ 9 ]
Legacy_Person{
description:	
现实人物

id	[...]
url	[...]
name	[...]
images	{...}
name_cn	[...]
comment	[...]
collects	[...]
info	Legacy_MonoInfo{...}
}
Legacy_Character{
description:	
虚拟角色

id	[...]
url	[...]
name	[...]
images	{...}
name_cn	[...]
comment	[...]
collects	[...]
info	Legacy_MonoInfo{...}
actors	[...]
}
Legacy_MonoBase{
description:	
人物（基础模型）

id	[...]
url	[...]
name	[...]
images	{...}
}
Legacy_Mono{
description:	
人物

id	[...]
url	[...]
name	[...]
images	{...}
name_cn	[...]
comment	[...]
collects	[...]
}
Legacy_MonoInfo{
description:	
人物信息

birth	[...]
height	[...]
gender	[...]
alias	{...}
source	{...}
name_cn	[...]
cv	[...]
}
Subject IDinteger
title: Subject ID
minimum: 1
条目 ID

User{
description:	
实际的返回值可能包括文档未声明的 url 字段，此字段主要用于开发者从 api 响应直接转跳到网页。 客户端开发者请不用依赖于此特性，此字段的值随时可能会改变。

id*	ID[...]
username*	Username[...]
nickname*	Nickname[...]
user_group*	UserGroup[...]
avatar*	Avatar{...}
example: { "large": "https://lain.bgm.tv/pic/user/l/000/00/00/1.jpg?r=1391790456", "medium": "https://lain.bgm.tv/pic/user/m/000/00/00/1.jpg?r=1391790456", "small": "https://lain.bgm.tv/pic/user/s/000/00/00/1.jpg?r=1391790456" }
sign*	Sign[...]
}
example: { "avatar": { "large": "https://lain.bgm.tv/pic/user/l/000/00/00/1.jpg?r=1391790456", "medium": "https://lain.bgm.tv/pic/user/m/000/00/00/1.jpg?r=1391790456", "small": "https://lain.bgm.tv/pic/user/s/000/00/00/1.jpg?r=1391790456" }, "sign": "Awesome!", "username": "sai", "nickname": "Sai🖖", "id": 1, "user_group": 1 }
Avatar{
large*	Large[...]
medium*	Medium[...]
small*	Small[...]
}
example: { "large": "https://lain.bgm.tv/pic/user/l/000/00/00/1.jpg?r=1391790456", "medium": "https://lain.bgm.tv/pic/user/m/000/00/00/1.jpg?r=1391790456", "small": "https://lain.bgm.tv/pic/user/s/000/00/00/1.jpg?r=1391790456" }
UserGroupinteger
title: UserGroup
用户组 - 1 = 管理员 - 2 = Bangumi 管理猿 - 3 = 天窗管理猿 - 4 = 禁言用户 - 5 = 禁止访问用户 - 8 = 人物管理猿 - 9 = 维基条目管理猿 - 10 = 用户 - 11 = 维基人

Enum:
Array [ 9 ]
BloodTypeinteger
title: BloodType
Blood type of a person. A, B, AB, O

Enum:
Array [ 4 ]
Character{
id*	ID[...]
name*	Name[...]
type*	CharacterType[...]
images	Images{...}
summary*	Summary[...]
locked*	Locked[...]
infobox	Infobox[...]
gender	Gender[...]
blood_type	BloodType[...]
birth_year	Birth Year[...]
birth_mon	Birth Mon[...]
birth_day	Birth Day[...]
stat*	Stat{...}
}
CharacterPerson{
id*	ID[...]
name*	Name[...]
type*	CharacterType[...]
images	Images{...}
subject_id*	Subject ID[...]
subject_type*	SubjectType[...]
subject_name*	Subject Name[...]
subject_name_cn*	Subject Name Cn[...]
staff	Staff[...]
}
CharacterTypeinteger
title: CharacterType
type of a character 角色，机体，舰船，组织...

Enum:
Array [ 4 ]
CollectionTypeinteger
title: CollectionType
example: 3
1: 想看
2: 看过
3: 在看
4: 搁置
5: 抛弃
Enum:
Array [ 5 ]
EpisodeCollectionTypeinteger
title: EpisodeCollectionType
example: 2
0: 未收藏
1: 想看
2: 看过
3: 抛弃
Enum:
Array [ 3 ]
Creator{
description:	
意义同Me

username*	Username[...]
nickname*	Nickname[...]
}
DetailedRevision{
id*	ID[...]
type*	Type[...]
creator	Creator{...}
summary*	Summary[...]
created_at*	Created At[...]
data	Data{...}
}
PersonRevision{
id*	ID[...]
type*	Type[...]
creator	Creator{...}
summary*	Summary[...]
created_at*	Created At[...]
data	Data{...}
}
PersonRevisionDataItem{
prsn_infobox*	Person Infobox[...]
prsn_summary*	Person Summary[...]
profession*	PersonRevisionProfession{...}
extra*	RevisionExtra{...}
prsn_name*	Person Name[...]
}
PersonRevisionProfession{
producer	Producer[...]
mangaka	Mangaka[...]
artist	Artist[...]
seiyu	Seiyu[...]
writer	Writer[...]
illustrator	Illustrator[...]
actor	Actor[...]
}
RevisionExtra{
img	Image[...]
}
SubjectRevision{
id*	ID[...]
type*	Type[...]
creator	Creator{...}
summary*	Summary[...]
created_at*	Created At[...]
data	SubjectRevisionData{...}
}
SubjectRevisionData{
field_eps*	Field EPs[...]
field_infobox*	Field Infobox[...]
field_summary*	Field Summary[...]
name*	Name[...]
name_cn*	Name CN[...]
platform*	Platform[...]
subject_id*	Subject ID[...]
type*	Type[...]
type_id*	Type ID[...]
vote_field*	Vote Field[...]
}
CharacterRevision{
id*	ID[...]
type*	Type[...]
creator	Creator{...}
summary*	Summary[...]
created_at*	Created At[...]
data	Data{...}
}
CharacterRevisionDataItem{
infobox*	Character Infobox[...]
summary*	Character Summary[...]
name*	Character Name[...]
extra*	RevisionExtra{...}
}
EpTypeinteger
title: EpType
本篇 = 0 特别篇 = 1 OP = 2 ED = 3 预告/宣传/广告 = 4 MAD = 5 其他 = 6

Enum:
Array [ 7 ]
Episode{
id*	ID[...]
type*	Type[...]
name*	Name[...]
name_cn*	Name Cn[...]
sort*	Sort[...]
ep	Ep[...]
airdate*	Airdate[...]
comment*	Comment[...]
duration*	Duration[...]
desc*	Desc[...]
disc*	Disc[...]
duration_seconds	[...]
}
example: { "airdate": "", "comment": 0, "desc": "", "disc": 0, "duration": "", "ep": 6, "id": 8, "name": "蒼と白の境界線", "name_cn": "", "sort": 6, "subject_id": 15, "type": 0, "duration_seconds": 1440 }
EpisodeDetail{
id*	ID[...]
type*	EpType[...]
name*	Name[...]
name_cn*	Name Cn[...]
sort*	Sort[...]
ep	Ep[...]
airdate*	Airdate[...]
comment*	Comment[...]
duration*	Duration[...]
desc*	Desc[...]
disc*	Disc[...]
subject_id*	Subject ID[...]
}
ErrorDetail{
title*	Title[...]
description*	Description[...]
details	Detail{...}
}
Images{
large*	Large[...]
common*	Common[...]
medium*	Medium[...]
small*	Small[...]
grid*	Grid[...]
}
Index{
id*	ID[...]
title*	Title[...]
desc*	Desc[...]
total	Total[...]
stat*	Stat{...}
created_at*	Created At[...]
updated_at*	Updated At[...]
creator*	Creator{...}
ban*	Ban[...]
nsfw*	目录是否包括 nsfw 条目[...]
}
IndexSubject{
description:	
同名字段意义同Subject

id*	ID[...]
type*	Type[...]
name*	Name[...]
images	Images{...}
infobox	Infobox[...]
date	Date[...]
comment*	Comment[...]
added_at*	Added At[...]
}
IndexBasicInfo{
description:	
新增或修改条目的内容，同名字段意义同Subject

title	Title[...]
description	Description[...]
}
IndexBasicInfo{
description:	
新增某条目到目录的请求信息

subject_id	Subject ID[...]
sort	Sort[...]
comment	Comment[...]
}
IndexBasicInfo{
description:	
修改目录中条目的信息

sort	Sort[...]
comment	Comment[...]
}
Infobox[
title: Infobox
example: [ { "key": "简体中文名", "value": "鲁路修·兰佩路基" }, { "key": "别名", "value": [ { "v": "L.L." }, { "v": "勒鲁什" }, { "v": "鲁鲁修" }, { "v": "ゼロ" }, { "v": "Zero" }, { "k": "英文名", "v": "Lelouch Lamperouge" }, { "k": "第二中文名", "v": "鲁路修·冯·布里塔尼亚" }, { "k": "英文名二", "v": "Lelouch Vie Britannia" }, { "k": "日文名", "v": "ルルーシュ・ヴィ・ブリタニア" } ] }, { "key": "性别", "value": "男" }, { "key": "生日", "value": "12月5日" }, { "key": "血型", "value": "A型" }, { "key": "身高", "value": "178cm→181cm" }, { "key": "体重", "value": "54kg" }, { "key": "引用来源", "value": "Wikipedia" } ]
Item{
key*	Key[...]
value*	Value{...}
}]
Page{
total*	Total[...]
limit*	Limit[...]
offset*	Offset[...]
}
Paged[Subject]{
total	Total[...]
limit	Limit[...]
offset	Offset[...]
data	Data[...]
}
Paged[Character]{
total	Total[...]
limit	Limit[...]
offset	Offset[...]
data	Data[...]
}
Paged[Person]{
total	Total[...]
limit	Limit[...]
offset	Offset[...]
data	Data[...]
}
Paged[Episode]{
total	Total[...]
limit	Limit[...]
offset	Offset[...]
data	Data[...]
}
Paged[IndexSubject]{
total	Total[...]
limit	Limit[...]
offset	Offset[...]
data	Data[...]
}
Paged[Revision]{
total	Total[...]
limit	Limit[...]
offset	Offset[...]
data	Data[...]
}
Paged[UserCollection]{
total	Total[...]
limit	Limit[...]
offset	Offset[...]
data	Data[...]
}
Paged[UserCharacterCollection]{
total	Total[...]
limit	Limit[...]
offset	Offset[...]
data	Data[...]
}
Paged[UserPersonCollection]{
total	Total[...]
limit	Limit[...]
offset	Offset[...]
data	Data[...]
}
Person{
id*	ID[...]
name*	Name[...]
type*	PersonType[...]
career*	[...]
images	Images{...}
short_summary*	Short Summary[...]
locked*	Locked[...]
}
PersonCareerstring
title: PersonCareer
An enumeration.

Enum:
Array [ 7 ]
PersonCharacter{
id*	ID[...]
name*	Name[...]
type*	CharacterType[...]
images	Images{...}
subject_id*	Subject ID[...]
subject_type*	SubjectType[...]
subject_name*	Subject Name[...]
subject_name_cn*	Subject Name Cn[...]
staff	Staff[...]
}
PersonDetail{
id*	ID[...]
name*	Name[...]
type*	PersonType[...]
career*	[...]
images	Images{...}
summary*	Summary[...]
locked*	Locked[...]
last_modified*	Last Modified[...]
infobox	Infobox[...]
gender	Gender[...]
blood_type	BloodType[...]
birth_year	Birth Year[...]
birth_mon	Birth Mon[...]
birth_day	Birth Day[...]
stat*	Stat{...}
}
PersonImages
PersonType
RelatedCharacter
RelatedPerson
UserCharacterCollection
UserPersonCollection
Revision
Stat
Subject
SlimSubject
Tags
SubjectType
SubjectBookCategory
SubjectAnimeCategory
SubjectGameCategory
SubjectRealCategory
SubjectCategory
UserSubjectCollection
UserSubjectCollectionModifyPayload
UserEpisodeCollection
RelatedSubject
SubjectRelation
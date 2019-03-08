
def say(**kwargs):
	print(kwargs)

class Section(dict):
	def __init__(self, text, type="mrkdwn"):
		self['type'] = "section"
		self['text'] = {}
		self['text']['type'] = type
		self['text']['text'] = text

class Image(dict):
	def __init__(self, image_url, image_alt_text='', title_type='plain_text', title_text='', title_emoji=True):
		self['type'] = 'image'
		self['image_url'] = image_url
		self['alt_text'] = image_alt_text
		self['title'] = dict(
			type=title_type,
			text=title_text,
			emoji=title_emoji
		)

class SectionWithImage(Section):
	def __init__(self, image_url, image_alt_text=' ', section_text=' ', section_type="mrkdwn"):
		super().__init__(text=section_text, type=section_type)
		self['accessory'] = dict(
			type="image",
			image_url=image_url,
			alt_text=image_alt_text
		)

class Field(dict):
	def __init__(self, text, type='mrkdwn'):
		self['text'] = text
		self['type'] = type

class SectionWithFields(dict):
	def __init__(self, fields):
		self['type'] = 'section'
		self['fields'] = fields

class Divider(dict):
	def __init__(self):
		self['type'] = 'divider'

class Context(dict):
	def __init__(self, text, type='mrkdwn', emoji=False):
		self['type'] = 'context'
		self['elements'] = dict(
			type=type,
			text=text,
			emoji=emoji
		)

class SlackBlockkitBlock (dict):
	def __init__(self, **kwargs):
		super().__init__(kwargs)

class SectionBlock(SlackBlockkitBlock):
	def __init__(self, text, type="mrkdwn"):
		self['type']="section"
		self['text']={}
		self['text']['type']=type
		self['text']['text']=text

class ImageBlock(SlackBlockkitBlock):
	def __init__(self, image_url, image_alt_text='', title_type='plain_text', title_text='', title_emoji=True):
		self['type']='image'
		self['image_url']=image_url
		self['alt_text']=image_alt_text
		self['title']=dict(
			type=title_type,
			text=title_text,
			emoji=title_emoji
		)

class ContextBlock(SlackBlockkitBlock):
	def __init__(self, text, type='mrkdwn', emoji=False):
		self['type']='context'
		self['elements']=dict(
			type=type,
			text=text,
			emoji=emoji
		)

class SectionWithImageBlock(SlackBlockkitBlock):
	def __init__(self, image_url, image_alt_text=' ', section_text=' ', section_type="mrkdwn"):
		super().__init__(text=section_text, type=section_type)
		self['accessory']=dict(
			type="image",
			image_url=image_url,
			alt_text=image_alt_text
		)

class DividerBlock(SlackBlockkitBlock):
	def __init__(self):
		self['type']='divider'

class SectionWithFieldsBlock(SlackBlockkitBlock):
	field_limit=10

	def add_field(self, text, type='mrkdwn'):
		field={}
		field['text']=text
		field['type']=type
		if len(self['fields'])<self.field_limit:
			self['fields'].append(field)
		else:
			raise Exception(f'Section With Fields Blocks are limited to {self.field_limit} fields.')

	def add_fields(self, l):
		for field in l:
			self.add_field(field)
		return self

	def __init__(self):
		self['type']='section'
		self['fields']=[]

def sectionwithfieldsblock_factory(fields_text: list):
	l=[]
	i=0

	def divide_chunks(l, n):
		# looping till length l
		for i in range(0, len(l), n):
			yield l[i:i + n]

	fields_text_chunked = divide_chunks(fields_text, SectionWithFieldsBlock.field_limit)

	return [SectionWithFieldsBlock().add_fields(fields_subset) for fields_subset in fields_text_chunked]


class Slack():
	def __init__(self, hook_url, channel_url=None):
		self.hook_url=hook_url
		self.channel_url=channel_url

	def post(self, message='', text='New Message', blocks=[], blocks_prefix=[]):
		import json
		import requests
		url = self.hook_url
		if message:
			message_block=SectionBlock(text=message)
			blocks=[*blocks_prefix, message_block, *blocks]

		content = dict(text=text, blocks=blocks)
		req = requests.post(url=url, json=content)
		req.raise_for_status()
		pass

	def post_remaining_budgets (sbk, teams):
		#teams=draft_manager.teams_with_budget
		section=SectionBlock(text='*Remaining Budgets:*')
		fields = [sbk.Field(f"*{team['owner_name']}:* ${team['budget']}M") for team in teams]
		blocks=[DividerBlock(),section, SectionWithFieldsBlock(fields=fields), DividerBlock()]
		return blocks

	# def post_information(self, info=[]):

	def post_message(self, message, message_title=None):
		if not message_title:
			message_title = message
		self.post(message, message_title)

	def post_fields (self, text=[], title_text=''):
		blocks=[]

		blocks += [DividerBlock()]
		if title_text: blocks += [SectionBlock(text=title_text)]
		blocks += [*sectionwithfieldsblock_factory(text)]
		blocks += [DividerBlock()]
		self.post(blocks=blocks)
		return blocks

	def films_block (sbk, films, title=None):
		blocks=[]
		if title:
			section=SectionBlock(text=title)
			blocks += section
		fields_text=[film['title'] for film in films]

		blocks += sectionwithfieldsblock_factory(fields_text)

		return blocks

	def post_drafted_films (sbk,draft_manager, title=None):

		if title: section=SectionBlock(text=title)

		fields = [sbk.Field(f"*{teams['owner_name']}*: {', '.join([film['title']+'(' + film['purchase_price'] + ')' for film in teams['films']])}") for teams in draft_manager.teams.values()]

		blocks = [section,*[SectionWithFieldsBlock(fields=fields_subset) for fields_subset in divide_chunks(fields, 10)]]
		# for subset in divide_chunks(draft_manager.remaining_films, 10):
		# blocks = divide_chunks(blocks, 10)
		return blocks

	def post_film_block(self, body_text, message_title='', image_url=None):
		blocks=[]
		blocks.append(DividerBlock())

		if image_url:
			blocks.append(SectionWithImageBlock(
				image_url=image_url,
				section_text=body_text
			))
		else:
			blocks.append(SectionBlock(body_text))

		blocks.append(DividerBlock())

		r=self.post(blocks=blocks, text=message_title)
		return r



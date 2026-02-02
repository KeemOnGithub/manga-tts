import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    device_map="cuda:0",
    dtype=torch.bfloat16
    # attn_implementation="flash_attention_2",
)

# single inference
wavs, sr = model.generate_voice_design(
    text="""
    The Tokyo campus was in the firmest grip of Autumn. The trees that lined the stairs up past the torii gate were heavy with leaves of every shade between red and gold, and the dried, fallen ones on the ground scraped across the concrete steps with each sigh of the wind.

The shrine at the top of the stairs was well tended, and though it was just one of many on the campus, this was the most private and remote. Utahime approached, stopping first at the water basin under a small pavilion to dash water over her hands, a ritual she had learned by heart as a girl. Only then did she approach the shrine and the bell hanging at the entrance. The deep red rope swung gently in the breeze and Utahime grasped it firmly to pull once, until the sweet chimes rung out clearly across hillside.

It was said that the gods would hear that bell and come to listen to her prayers. Utahime wasn’t sure she had ever really believed in all that, but there was still comfort to take in closing her eyes and pressing her hands together, and hoping that there was some power out there that might hear her and give her a turn of kindness.

Please let this be the right decision…

She bowed low and felt the wind gently tug at her hair and clothes, almost like a reassuring whisper. After several seconds she straightened and opened her eyes - 

To find Gojo standing tall before her, accepting her prayers as if they were for him. “You rang?” he drawled.

And please strike this man down with a bolt of lightning.

“Go away,” she ground out, trying valiantly to keep her hands together. “Heretic.”

“I thought all this miko stuff was for show… don’t tell me you actually believe in this nonsense?” He jerked his thumb over his shoulder at the shrine - the one that had been standing for over a thousand years. Tradition had never meant anything to Gojo.

Giving up on her prayers, Utahime dropped her hands and headed for the top of the stairs that led back down toward the main campus. She had only taken a detour on her way to meet Shoko. Now there was no reason for further delay.

Unfortunately, Gojo comfortably caught up with her on his much longer legs, following her down the steps. “If you need someone to answer your prayers, Utahime, you need only ask,” he said, pushing his hands deep into his pockets.

Utahime ignored him. She’d been hoping he wouldn’t be here. Since he’d graduated, Gojo only stopped by the campus to collect assignments and deliver reports like every other sorcerer on the official payroll. She’d heard that he took an absurd number of jobs, to the point where Shoko frequently complained that he didn’t seem to take any time off. Each day, every day, he was working. Bumping into him was rare, for on any given day he might be in Sapporo or Nagasaki, or both, handling jobs alone that normally took whole teams. 

The gulf between someone like him and someone like her was wide and widening all the time.

“You can answer my prayers by leaving me alone,” she told him, skewing him a glare.

He only laughed, like they were sharing a joke. It was still strange to see him out of his school uniform, in just jeans and high-collared jacket. He’d changed his shades recently too, swapping out the fashionable round ones for a much more opaque wrap-around pair that almost totally concealed his eyes. According to Shoko, his eyes were getting more powerful every year and giving him fatigue. Not that this was a guy who ever seemed short on energy.

“You here for an assignment?” he asked her.

“No,” she said simply.

“Oh? You’re being fired?” He grinned. “I told you not to ask questions about Yaga’s Panda baby thing. Just gotta smile and nod.”

“I’m not being fired,” she said testily, then she stopped on the steps. “But I am leaving.”

Gojo continued down the steps for a moment before he also stopped and turned back to her. They were almost eye level, and though the shades concealed so much of his expression, she saw the smile had slid from his face. “What do you mean?” The humour had abandoned his voice.

“I’m giving up front-line sorcery and I’m leaving Tokyo,” she said, and pushing it out into the air made it more real than when it had just been written down on official letters and emails. “I’ve accepted a post at the Kyoto campus… I’ll be a teacher.”

The ghost of an uncertain smile chases across his face. “You’re lying,” he said. “Shoko would have told me.”

“I haven’t told Shoko yet,” she said heavily. That was what she had come here for, and it was a conversation she was dreading. She knew Shoko would be happy for her, but moving to another city so far away was going to change their relationship in a profound way.

“But Kyoto is boring,” said Gojo, pulling a face. “Everyone talks like a hick and their baseball team sucks.”

“I’m from Kyoto,” she reminded him. “This way I get to be closer to my family and my old friends. And maybe… maybe I can finally do something I’m good at.”

“You’re good at sorcery!” he cried.

She blinked at him, surprised.

Gojo rubbed the back of his head and looked away. Why did he look so agitated all of a sudden? His boot tapped restlessly on the step and he chewed his lip as he stared into the trees. Utahime watched him, wondering if that was the closest he had ever come to complimenting her. “Why not Tokyo?” he asked. “There’s positions here at the college.”

“But they’re more short-staffed over there. And… it’s a chance to start over,” she said quietly.

His head turned to her once more, questioning.

“I’m just a country girl, Gojo. The sorcerers here… I can’t compete. I’ve always been completely overshadowed by everyone. I’ll never be promoted if I stay here and I’ll never be anything more than the weakest. If I’m ever to grow, I have to leave.”

Gojo eased up onto the same step as her and his shadow fell across her face. “Am I casting too much shade for you to grow, little Utahime?” he asked.

Her brow pinched. “This has nothing to do with you,” she huffed, stepping back out into the sun. “You are not the centre of the universe.”

“I beg to differ!”

Utahime hurried down the steps, past the rows of stone lanterns like tiny houses. She passed under the red torii gate and looked back to see Gojo had hardly moved. He still looked perplexingly annoyed. “I think it’s a mistake!” he called down to her. “Who wants to be a teacher? Kids suck!”

“You suck!” she yelled back.

“The pay is shit and everyone here will forget you exist!”

“Including you? Good!”

He was losing this argument and struggling to form a response, but why were they even arguing? Why did he care? She hadn’t even been meaning to tell him… it had just slipped out; a practice-run for how she would tell Shoko once she reached the clinic where her friend was interning. Now Gojo looked like a child who’d dropped his ice cream. “You’ll hate it,” he said shortly. “And you’ll miss this place.”

“Is that what you think?”

His mouth set in a grim line.

Something strange was going on. Utahime narrowed her eyes, noticing the colour had risen in his cheeks despite the cool day. “I guess you’ll have to find someone new to pick on,” she said lightly.

“Oh, you think a three hour bullet train is going to stop me?” he asked. “I can warp, remember? I can be there in 3 seconds flat to give you grief.”

She raised her hands, a picture of astonished confusion. “So what are you worried about?” 

He pushed a hand through his hair. “It won’t be the same.”

She shrugged, hardly knowing what to say to that. “It’s not supposed to always be the same forever, I guess.” And who would want that? She was a struggling sorcerer who could hardly afford her own apartment, living with people she couldn’t relate to. Something had to give. “Sometimes you’ve got to make a change to get the things you really want.”

The fight drained from him. “And this is what you really want?”

Well, it wasn’t her dream come true, but it was the path that had opened up to her, and she’d be a fool not to take it. “It is,” she said instead.

He lapsed into silence. She thought he might have been looking off over her head, but it was hard to tell with those obscure shades.

Sensing the conversation was done, Utahime half turned. “I’m going to see Shoko to let her know. I’ll be leaving on Friday.”

She thought he might be too sullen to respond, but he stirred slightly as she began to walk away. “Send me a souvenir?”

Over her shoulder she flashed him a quick smile. “Sure.”

Gojo’s smile in response was small, almost shy, and quickly gone. She left him on the steps and went in search of the clinic to find Shoko. As she expected, Shoko’s response made more sense - there were tears of upset but laughter and smiles too. Shoko was happy for her. Glad for her. Relieved that she would be leaving behind the front line work to put her true strengths into action as an educator. 

When Friday came, Utahime crammed all her belongings into her father’s car and set off for her new home and her new life. She had not seen Gojo since she’d left him on the steps by the shrine, but she dismissed him from her mind. It could only be a bonus to be away from someone like him, but she sensed it might be a while until she was truly free from his shadow.
    """,
    language="English",
    instruct="This is a book excerpt, so you must speak expressively at a medium pace. Speak with a light male voice."
)
sf.write("output_voice_design.wav", wavs[0], sr)

# # batch inference
# wavs, sr = model.generate_voice_design(
#     text=[
#       "哥哥，你回来啦，人家等了你好久好久了，要抱抱！",
#       "It's in the top drawer... wait, it's empty? No way, that's impossible! I'm sure I put it there!"
#     ],
#     language=["Chinese", "English"],
#     instruct=[
#       "体现撒娇稚嫩的萝莉女声，音调偏高且起伏明显，营造出黏人、做作又刻意卖萌的听觉效果。",
#       "Speak in an incredulous tone, but with a hint of panic beginning to creep into your voice."
#     ]
# )
# sf.write("output_voice_design_1.wav", wavs[0], sr)
# sf.write("output_voice_design_2.wav", wavs[1], sr)
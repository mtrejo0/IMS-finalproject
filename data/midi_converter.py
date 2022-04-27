import mido
mid = mido.MidiFile('corneria-2-.mid', clip=True)
mid.tracks
for m in mid.tracks[2][:]:
    print(m)